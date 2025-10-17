from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count
from django.utils.dateparse import parse_datetime, parse_date
from django.utils import timezone
from django.core.cache import cache
from problem_types.models import ProblemType
from user_messages.models import Message
from polls.models import Poll, PollOption, PollVote
from feeds.models import Feed, FeedReaction
from institutions.models import Institution, Department
import datetime


def _parse_range(start_str, end_str):
	"""Return (start_dt, end_dt) aware datetimes or (None, None)."""
	start = None
	end = None
	if start_str:
		dt = parse_datetime(start_str) or parse_date(start_str)
		if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
			start = datetime.datetime.combine(dt, datetime.time.min)
		else:
			start = dt
	if end_str:
		dt = parse_datetime(end_str) or parse_date(end_str)
		if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
			end = datetime.datetime.combine(dt, datetime.time.max)
		else:
			end = dt
	if start and timezone.is_naive(start):
		start = timezone.make_aware(start, timezone.get_current_timezone())
	if end and timezone.is_naive(end):
		end = timezone.make_aware(end, timezone.get_current_timezone())
	return start, end


class AdminAnalyticsView(APIView):
	permission_classes = [IsAdminUser]

	def get(self, request):
		# Query params: start, end (ISO date or datetime), institution (id), daily (true/false), per_feed (true/false)
		start_str = request.query_params.get('start')
		end_str = request.query_params.get('end')
		institution_id = request.query_params.get('institution')
		daily = request.query_params.get('daily', 'false').lower() in ('1', 'true', 'yes', 'on')
		per_feed = request.query_params.get('per_feed', 'false').lower() in ('1', 'true', 'yes', 'on')

		cache_key = f"analytics:admin:{request.get_full_path()}"
		cached = cache.get(cache_key)
		if cached is not None:
			return Response(cached)

		start, end = _parse_range(start_str, end_str)

		# Base filters
		msg_qs = Message.objects.all()
		fr_qs = FeedReaction.objects.all()
		pv_qs = PollVote.objects.all()

		if start:
			msg_qs = msg_qs.filter(timestamp__gte=start)
			fr_qs = fr_qs.filter(created_at__gte=start)
			pv_qs = pv_qs.filter(created_at__gte=start)
		if end:
			msg_qs = msg_qs.filter(timestamp__lte=end)
			fr_qs = fr_qs.filter(created_at__lte=end)
			pv_qs = pv_qs.filter(created_at__lte=end)
		if institution_id:
			msg_qs = msg_qs.filter(institution_id=institution_id)
			# for messages_by_department we'll still compute departments for that institution

		# 1) Problem type stats
		problem_counts = (
			msg_qs.values('problem_type')
			.annotate(count=Count('id'))
			.order_by('-count')
		)
		problem_type_map = {pt.id: pt.name for pt in ProblemType.objects.all()}
		problem_type_stats = [
			{
				'problem_type_id': p['problem_type'],
				'problem_type_name': problem_type_map.get(p['problem_type'], 'Other'),
				'count': p['count']
			}
			for p in problem_counts
		]

		# 2) Poll stats (accurate per date range)
		poll_stats = []
		polls = Poll.objects.all()
		for poll in polls:
			# filter votes by poll and date range
			votes = pv_qs.filter(poll_id=poll.id)
			total_voters = votes.count()
			options = []
			for opt in poll.options.all():
				opt_count = votes.filter(selected_options=opt).count()
				options.append({'option_id': opt.id, 'text': opt.text, 'votes_count': opt_count})
			poll_stats.append({
				'poll_id': poll.id,
				'question': poll.question,
				'total_voters': total_voters,
				'options': options,
			})

		# 3) Feed reactions
		total_reactions = fr_qs.count()
		reaction_breakdown = fr_qs.values('reaction_type').annotate(count=Count('id'))
		reaction_map = {r['reaction_type']: r['count'] for r in reaction_breakdown}
		per_feed_list = []
		if per_feed:
			feeds = Feed.objects.all()
			if institution_id:
				feeds = feeds.filter(institution_id=institution_id)
			for f in feeds:
				fq = fr_qs.filter(feed_id=f.id)
				per_feed_list.append({
					'feed_id': f.id,
					'created_at': f.created_at,
					'total_reactions': fq.count(),
					'by_type': {r['reaction_type']: r['count'] for r in fq.values('reaction_type').annotate(count=Count('id'))}
				})

		# 4) Messages by institution and department (with names)
		messages_by_institution_qs = (
			msg_qs.values('institution').annotate(count=Count('id')).order_by('-count')
		)
		inst_map = {i.id: i.name for i in Institution.objects.all()}
		messages_by_institution = [
			{'institution_id': i['institution'], 'institution_name': inst_map.get(i['institution'], ''), 'count': i['count']}
			for i in messages_by_institution_qs
		]

		messages_by_department_qs = (
			msg_qs.values('department').annotate(count=Count('id')).order_by('-count')
		)
		dept_map = {d.id: f"{d.name} ({d.institution.name})" for d in Department.objects.select_related('institution').all()}
		messages_by_department = [
			{'department_id': d['department'], 'department_name': dept_map.get(d['department'], ''), 'count': d['count']}
			for d in messages_by_department_qs
		]

		# 5) Optional daily breakdown for messages per institution
		messages_daily = None
		if daily and start and end:
			# build date buckets
			delta = (end.date() - start.date()).days if hasattr(end, 'date') and hasattr(start, 'date') else 0
			daily_data = {}
			for single_day in (start.date() + datetime.timedelta(n) for n in range(delta + 1)):
				day_start = timezone.make_aware(datetime.datetime.combine(single_day, datetime.time.min))
				day_end = timezone.make_aware(datetime.datetime.combine(single_day, datetime.time.max))
				day_qs = Message.objects.filter(timestamp__range=(day_start, day_end))
				if institution_id:
					day_qs = day_qs.filter(institution_id=institution_id)
				counts = list(day_qs.values('institution').annotate(count=Count('id')))
				daily_data[str(single_day)] = counts
			messages_daily = daily_data

		result = {
			'problem_type_stats': problem_type_stats,
			'poll_stats': poll_stats,
			'feed_reactions': {
				'total': total_reactions,
				'by_type': reaction_map,
				'per_feed': per_feed_list,
			},
			'messages_by_institution': messages_by_institution,
			'messages_by_department': messages_by_department,
			'messages_daily': messages_daily,
		}

		# Cache short-lived (60s)
		try:
			cache.set(cache_key, result, timeout=60)
		except Exception:
			pass

		return Response(result)
