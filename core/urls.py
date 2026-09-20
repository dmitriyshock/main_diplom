from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('prices/', views.prices, name='prices'),
    path('contacts/', views.contacts, name='contacts'),
    path('privacy/', views.legal_page, {'document': 'privacy'}, name='privacy'),
    path('personal-data-consent/', views.legal_page, {'document': 'personal-data'}, name='personal_data'),
    path('cookies/', views.legal_page, {'document': 'cookies'}, name='cookies'),
    path('service-terms/', views.legal_page, {'document': 'terms'}, name='terms'),
    path('request/', views.contact_request, name='contact_request'),
]
