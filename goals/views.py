from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import GoalContributionForm, GoalForm
from .models import Goal, GoalContribution


class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = 'goals/goal_list.html'
    context_object_name = 'goals'
    paginate_by = 12

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class GoalDetailView(LoginRequiredMixin, DetailView):
    model = Goal
    template_name = 'goals/goal_detail.html'
    context_object_name = 'goal'

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user).prefetch_related(
            'contributions'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contributions'] = self.object.contributions.all()[:50]
        return context


class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'goals/goal_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nova Meta'
        context['action'] = 'create'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Meta "{self.object.name}" criada com sucesso!')
        return response


class GoalUpdateView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = 'goals/goal_form.html'

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Meta: {self.object.name}'
        context['action'] = 'update'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Meta atualizada com sucesso!')
        return response


class GoalDeleteView(LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = 'goals/goal_confirm_delete.html'
    success_url = reverse_lazy('goals:list')

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def form_valid(self, form):
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f'Meta "{name}" excluída com sucesso!')
        return response


class GoalContributionCreateView(LoginRequiredMixin, CreateView):
    model = GoalContribution
    form_class = GoalContributionForm
    template_name = 'goals/goal_contribution_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.goal = get_object_or_404(
            Goal, pk=kwargs['pk'], user=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['goal'] = self.goal
        return context

    def form_valid(self, form):
        form.instance.goal = self.goal
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Aporte de R$ {self.object.amount} registrado em "{self.goal.name}".',
        )
        return response

    def get_success_url(self):
        return reverse('goals:detail', kwargs={'pk': self.goal.pk})


class GoalContributionDeleteView(LoginRequiredMixin, DeleteView):
    model = GoalContribution
    template_name = 'goals/goal_contribution_confirm_delete.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return GoalContribution.objects.filter(
            user=self.request.user,
            goal_id=self.kwargs['goal_pk'],
        )

    def get_success_url(self):
        return reverse('goals:detail', kwargs={'pk': self.kwargs['goal_pk']})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Aporte excluído com sucesso!')
        return response
