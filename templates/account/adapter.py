from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponseRedirect
from django.urls import reverse

# class PredictAccountAdapter(DefaultAccountAdapter):
#
#     def respond_user_inactive(self, request, user):
#         return HttpResponseRedirect(reverse('account_inactive'))