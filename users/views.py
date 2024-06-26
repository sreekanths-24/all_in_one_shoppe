from django.views import View
from django.http import HttpResponseBadRequest
from django.views.generic import TemplateView, UpdateView
from braces.views import LoginRequiredMixin, StaffuserRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.shortcuts import (
    redirect,
    render,
)
from django.contrib.auth.decorators import login_required

from .forms import (
    CustomLoginForm,
    RegisterForm,
    UpdateForm,
    ForgetPasswordEmailCodeForm,
    ChangePasswordForm,
    OtpForm,
)
from .models import OtpCode, CustomUser
from .utils import (
    send_activation_code,
    send_reset_password_code,
    generate_otp

)
from .decorators import only_authenticated_user, redirect_authenticated_user


@redirect_authenticated_user
def login_view(request):
    error = None
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username_or_email'],
                password=form.cleaned_data['password'])
            if user:
                if not user.is_active:
                    messages.warning(request, _(
                        f"It's look like you haven't still verified your email, an otp is already sent to your email - {user.email}"))
                    return redirect('users:activate_email')
                else:
                    login(request, user)
                    if request.user.is_staff:
                        return redirect('mod:home')
                    return redirect(reverse_lazy("home:shop"))
            else:
                error = 'Invalid Credentials'
    else:
        form = CustomLoginForm()
    return render(request, 'users/login.html', {'form': form, 'error': error})


@only_authenticated_user
@login_required
def logout_view(request):
    logout(request)
    return redirect('users:login')


@redirect_authenticated_user
def registeration_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST or None)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.source = 'Register'
            user.save(True)
            return redirect("users:login")
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


@redirect_authenticated_user
def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgetPasswordEmailCodeForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username_or_email']
            user = get_user_model().objects.get(**username_or_email)
            code = generate_otp()

            otp = OtpCode(code=code, user=user, email=user.email)
            otp.save()

            try:
                send_reset_password_code(user.email, code)
            except:
                otp.delete()
                messages.error(request, _('Failed while sending code!'))
            else:
                messages.success(request, _(
                    f"We've sent a passwrod reset otp to your email - {user.email}"))
                return redirect('users:reset_code')
    else:
        form = ForgetPasswordEmailCodeForm()
    return render(request, 'users/forgot_password.html', context={'form': form})


@redirect_authenticated_user
def check_otp_view(request):
    if request.method == 'POST':
        form = OtpForm(request.POST)
        if form.is_valid():
            otp = OtpCode.objects.get(code=form.cleaned_data['otp'])
            user = otp.user
            otp.delete()
            user.is_active = True
            user.save()
            return redirect('users:login')
    else:
        form = OtpForm()
    return render(request, 'users/user_otp.html', {'form': form})


@redirect_authenticated_user
def check_reset_otp_view(request):
    if request.method == 'POST':
        form = OtpForm(request.POST)
        if form.is_valid():
            otp = OtpCode.objects.get(code=form.cleaned_data['otp'])
            request.session['email'] = otp.user.email
            messages.success(request, _(
                "Please create a new password that you don't use on any other site."))
            return redirect('users:reset_new_password')
    else:
        form = OtpForm()
    return render(request, 'users/user_otp.html', {'form': form})


@redirect_authenticated_user
def reset_new_password_view(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            email = request.session['email']
            del request.session['email']
            user = CustomUser.objects.get(email=email)
            user.password = make_password(form.cleaned_data["new_password2"])
            user.save()
            messages.success(request, _(
                "Your password changed. Now you can login with your new password."))
            return redirect('users:login')
    else:
        form = ChangePasswordForm()
    return render(request, 'users/new_password.html', {'form': form})


class ProfileView(TemplateView):
    template_name = "users/profile.html"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = get_user_model()
    form_class = UpdateForm
    template_name = "users/profile-update.html"
    success_url = reverse_lazy("users:profile")
    slug_url_kwarg = "name"
    slug_field = "username"


class ChangePasswordView(LoginRequiredMixin, StaffuserRequiredMixin, View):
    model = get_user_model()
    form_class = ChangePasswordForm
    template_name = "users/new_password.html"
    success_url = reverse_lazy("mod:home")

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": self.form_class()})

    def post(self, request, id):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = CustomUser.objects.get(id=id)
            user.password = make_password(form.cleaned_data["new_password2"])
            user.save()
            messages.success(request, _(
                "Your password changed. Now you can login with your new password."))
            return redirect('users:login')
        else:
            return HttpResponseBadRequest(f"form error {form.errors}")
