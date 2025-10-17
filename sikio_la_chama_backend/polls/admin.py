from django.contrib import admin
from .models import Poll, PollOption, PollVote

# -----------------------------
# PollOption Inline for PollAdmin
# -----------------------------
class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 1
    readonly_fields = ('votes_count',)


# -----------------------------
# Poll Admin
# -----------------------------
@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_by', 'start_at', 'end_at', 'created_at')
    list_filter = ('start_at', 'end_at', 'created_at', 'allow_multiple')
    search_fields = ('question', 'created_by__username')
    inlines = [PollOptionInline]


# -----------------------------
# PollVote Admin
# -----------------------------
@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ('poll', 'user', 'device_id', 'created_at', 'selected_options_display')
    list_filter = ('created_at', 'poll')
    search_fields = ('poll__question', 'user__username', 'device_id')

    def selected_options_display(self, obj):
        return ", ".join([option.text for option in obj.selected_options.all()])
    selected_options_display.short_description = "Selected Options"
