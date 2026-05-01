"""
Profile views for user profile management in the Finanpy financial system.

This module implements class-based views for profile functionality with:
- User data isolation and security
- Profile creation and editing capabilities
- Integration with Django's authentication system
- Responsive templates with TailwindCSS styling
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from typing import Any, Dict

from .models import Profile
from .forms import ProfileForm


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """
    Display user profile information with read-only view.
    
    This view shows comprehensive profile information for the authenticated user
    with proper data isolation. Only the profile owner can view their profile.
    """
    model = Profile
    template_name = 'profiles/profile_detail.html'
    context_object_name = 'profile'
    
    def get_object(self, queryset=None):
        """
        Get the profile for the current authenticated user.
        Creates profile if it doesn't exist.
        """
        try:
            # Try to get existing profile
            profile = Profile.objects.get(user=self.request.user)
            return profile
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = Profile.objects.create(user=self.request.user)
            messages.info(
                self.request, 
                'Perfil criado automaticamente. Complete suas informações pessoais.'
            )
            return profile
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Add additional context data for the template.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = self.get_object()
        
        # Calculate profile completion percentage. first/last name now live on User.
        completion_fields = [
            profile.user.first_name,
            profile.user.last_name,
            profile.phone,
            profile.birth_date,
            profile.bio
        ]
        completed_fields = sum(1 for field in completion_fields if field)
        completion_percentage = int((completed_fields / len(completion_fields)) * 100)
        
        # Add context data
        context.update({
            'user': user,
            'completion_percentage': completion_percentage,
            'completed_fields': completed_fields,
            'total_fields': len(completion_fields),
            'profile_age': profile.age,
            'can_edit': True,  # User can always edit their own profile
        })
        
        return context


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Update user profile information with form validation.
    
    This view allows authenticated users to edit their profile information
    with proper validation and user feedback. Only the profile owner can
    edit their profile.
    """
    model = Profile
    form_class = ProfileForm
    template_name = 'profiles/profile_edit.html'
    success_message = 'Perfil atualizado com sucesso!'
    context_object_name = 'profile'
    
    def get_object(self, queryset=None):
        """
        Get the profile for the current authenticated user.
        Creates profile if it doesn't exist.
        """
        try:
            # Try to get existing profile
            profile = Profile.objects.get(user=self.request.user)
            return profile
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = Profile.objects.create(user=self.request.user)
            messages.info(
                self.request,
                'Novo perfil criado. Preencha suas informações pessoais.'
            )
            return profile
    
    def get_success_url(self):
        """
        Redirect to profile detail view after successful update.
        """
        return reverse_lazy('profiles:detail')

    # NOTE: no custom form_valid. ProfileForm.save() already persists the User
    # name fields, the Profile fields and the avatar (or its removal). Calling
    # form.save() twice — as the previous override did — caused the avatar
    # file to be wiped by the pre_save signal on the second save. The success
    # message is provided by SuccessMessageMixin via `success_message` above.
    
    def form_invalid(self, form):
        """
        Handle form validation errors with user-friendly messages.
        """
        # Count the number of errors
        error_count = sum(len(errors) for errors in form.errors.values())
        
        if error_count == 1:
            messages.error(
                self.request,
                'Por favor, corrija o erro indicado no formulário.'
            )
        else:
            messages.error(
                self.request,
                f'Por favor, corrija os {error_count} erros indicados no formulário.'
            )
        
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Add additional context data for the template.
        """
        context = super().get_context_data(**kwargs)
        profile = self.get_object()
        
        # Calculate current completion percentage. first/last name now live on User.
        completion_fields = [
            profile.user.first_name,
            profile.user.last_name,
            profile.phone,
            profile.birth_date,
            profile.bio
        ]
        completed_fields = sum(1 for field in completion_fields if field)
        completion_percentage = int((completed_fields / len(completion_fields)) * 100)
        
        # Add helpful context
        context.update({
            'completion_percentage': completion_percentage,
            'completed_fields': completed_fields,
            'total_fields': len(completion_fields),
            'is_edit_view': True,
            'cancel_url': reverse_lazy('profiles:detail'),
        })
        
        return context
