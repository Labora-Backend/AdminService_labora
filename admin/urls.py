from django.urls import path
from . import views

urlpatterns = [
    # User Management
    path('users/', views.view_all_users, name='view_all_users'),
    path('users/<str:role>/<int:user_id>/block/', views.block_user, name='block_user'),
    path('users/<str:role>/<int:user_id>/unblock/', views.unblock_user, name='unblock_user'),
    path('users/verify/', views.verify_user, name='verify_user'),

    # Payment Disputes
    path('disputes/', views.payment_disputes, name='payment_disputes'),
    path('disputes/<int:dispute_id>/', views.get_dispute_details, name='get_dispute_details'),
    path('disputes/<int:dispute_id>/resolve/', views.resolve_dispute, name='resolve_dispute'),

    # Reviews
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),

    # Notifications
    path('notifications/send/', views.send_notification, name='send_notification'),
    path('notifications/', views.view_all_notifications, name='view_all_notifications'),

    # Audit Logs
    path('logs/', views.admin_logs, name='admin_logs'),
]