from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Tag
from .forms import TagForm


class TagListView(LoginRequiredMixin, ListView):
    model = Tag
    template_name = 'tags/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 50

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class TagCreateView(LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag_form.html'
    success_url = reverse_lazy('tags:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Tag "{form.instance.name}" criada com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Nova Tag'
        context['form_action'] = 'Criar'
        return context


class TagUpdateView(LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag_form.html'
    success_url = reverse_lazy('tags:list')

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Tag "{form.instance.name}" atualizada!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Editar Tag'
        context['form_action'] = 'Salvar'
        return context


class TagDeleteView(LoginRequiredMixin, DeleteView):
    model = Tag
    template_name = 'tags/tag_confirm_delete.html'
    success_url = reverse_lazy('tags:list')

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f'Tag "{self.object.name}" removida.')
        return super().form_valid(form)
