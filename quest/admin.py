from django.contrib.admin import AdminSite
from django.db.models import Count, OuterRef, Subquery, IntegerField, Avg
from django.shortcuts import render
from django.urls import path

from goals.models import Goal, TaskStatus


# tag::admin-site[]
class QuestAdminSite(AdminSite):
    def get_urls(self):
        urls = super().get_urls() + [
            path('goal_dashboard_python/',
                 self.admin_view(
                     self.goals_dashboard_view_py)),
            path('goal_dashboard_sql/',
                 self.admin_view(
                     self.goals_dashboard_view_sql)),
            path('goal_dashboard_with_avg_completions/',
                 self.admin_view(
                     self.goals_avg_completions_view))
        ]
        return urls

# end::admin-site[]

# tag::counting-with-python[]
    def goals_dashboard_view_py(self, request):
        """Render the top ten goals by completed tasks.

        WARNING: Don't do this! This example is of an
        anti-pattern: running an inefficient calculation in
        Python that you could offload to the database
        instead. See the goals_dashboard_view_sql() view
        instead.
        """
        goals = Goal.objects.all()

        for g in goals:  # <1>
            completions = TaskStatus.objects.completed()
            completed_tasks = completions.filter(
                task__in=g.tasks.values('id'))  # <2>
            setattr(g, 'completed_tasks',
                    completed_tasks.count())  # <3>

        goals = sorted(goals, key=lambda g: g.completed_tasks,
                       reverse=True)[:10]  # <4>

        return render(request, "admin/goal_dashboard.html",
                      {"goals": goals})
# end::counting-with-python[]

# tag::counting-with-sql[]
    def goals_dashboard_view_sql(self, request):
        completed_tasks = Subquery(  # <1>
            TaskStatus.objects.filter(
                task__goal=OuterRef('pk'),  # <2>
                status=TaskStatus.DONE
            ).values(
                'task__goal'
            ).annotate(  # <3>
                count=Count('pk')
            ).values('count'),
            output_field=IntegerField())  # <4>

        goals = Goal.objects.all().annotate(
            completed_tasks=completed_tasks
        ).order_by('-completed_tasks')[:10]

        return render(request, "admin/goal_dashboard.html",
                      {"goals": goals})
# end::counting-with-sql[]

# tag::aggregations[]
    def goals_avg_completions_view(self, request):
        completed_tasks = Subquery(
            TaskStatus.objects.filter(
                task__goal=OuterRef('pk'),
                status=TaskStatus.DONE
            ).values(
                'task__goal'
            ).annotate(
                count=Count('pk')
            ).values('count'),
            output_field=IntegerField())

        goals = Goal.objects.all().annotate(
            completed_tasks=completed_tasks)
        top_ten_goals = goals.order_by('-completed_tasks')[:10]
        average_completions = goals.aggregate(
            Avg('completed_tasks'))  # <1>
        avg = int(average_completions['completed_tasks__avg'])

        other_stats = (
            {
                'name': 'Average Completed Tasks',
                'stat': avg
            },
        )
        return render(request, "admin/goal_dashboard.html", {
            "goals": top_ten_goals,
            "other_stats": other_stats
        })
# end::aggregations[]


admin_site = QuestAdminSite()
