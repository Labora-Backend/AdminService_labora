from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q
import requests
from .models import UserVerification, PaymentDispute, AdminActionLog
from .serializers import UserVerificationSerializer, PaymentDisputeSerializer
from .permissions import IsAdminUser


class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def log_admin_action(admin_id, action, target_type, target_id, description=""):
    AdminActionLog.objects.create(
        admin_id=admin_id,
        action_type=action,
        target_type=target_type,
        target_id=target_id,
        description=description
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def view_all_users(request):
    headers = {
        "Authorization": request.headers.get("Authorization")
    }
    try:
        client_res = requests.get(
            "http://client-service/api/clients/",
            headers=headers,
            timeout=5
        )
        freelancer_res = requests.get(
            "http://freelancer-service/api/freelancers/",
            headers=headers,
            timeout=5
        )
    except requests.exceptions.RequestException:
        return Response(
            {"error": "User services unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if client_res.status_code != 200 or freelancer_res.status_code != 200:
        return Response(
            {"error": "Failed to fetch users"},
            status=status.HTTP_502_BAD_GATEWAY
        )

    search_query = request.query_params.get('search', '')
    clients = client_res.json()
    freelancers = freelancer_res.json()

    if isinstance(clients, list) and search_query:
        clients = [u for u in clients if
                   search_query.lower() in str(u).get('name', '').lower() or search_query.lower() in str(u).get('email',
                                                                                                                '').lower()]
    if isinstance(freelancers, list) and search_query:
        freelancers = [u for u in freelancers if
                       search_query.lower() in str(u).get('name', '').lower() or search_query.lower() in str(u).get(
                           'email', '').lower()]

    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)

    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        page = 1
        page_size = 20

    start = (page - 1) * page_size
    end = start + page_size

    return Response(
        {
            "clients": clients[start:end] if isinstance(clients, list) else clients,
            "freelancers": freelancers[start:end] if isinstance(freelancers, list) else freelancers,
            "page": page,
            "page_size": page_size
        },
        status=status.HTTP_200_OK
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdminUser])
def block_user(request, role, user_id):
    if role not in ["client", "freelancer"]:
        return Response(
            {"error": "Invalid role. Must be 'client' or 'freelancer'"},
            status=status.HTTP_400_BAD_REQUEST
        )

    headers = {
        "Authorization": request.headers.get("Authorization")
    }
    service_url = (
        f"http://client-service/api/clients/{user_id}/block/"
        if role == "client"
        else f"http://freelancer-service/api/freelancers/{user_id}/block/"
    )

    try:
        response = requests.patch(service_url, headers=headers, timeout=5)
    except requests.exceptions.RequestException:
        return Response(
            {"error": "User service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if response.status_code == 200:
        log_admin_action(
            request.user.id,
            "BLOCK_USER",
            "user",
            user_id,
            f"{role} blocked"
        )
        return Response({"message": "User blocked"}, status=200)

    return Response({"error": "Failed to block user"}, status=400)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdminUser])
def unblock_user(request, role, user_id):
    if role not in ["client", "freelancer"]:
        return Response(
            {"error": "Invalid role. Must be 'client' or 'freelancer'"},
            status=status.HTTP_400_BAD_REQUEST
        )

    headers = {
        "Authorization": request.headers.get("Authorization")
    }
    service_url = (
        f"http://client-service/api/clients/{user_id}/unblock/"
        if role == "client"
        else f"http://freelancer-service/api/freelancers/{user_id}/unblock/"
    )

    try:
        response = requests.patch(service_url, headers=headers, timeout=5)
    except requests.exceptions.RequestException:
        return Response(
            {"error": "User service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if response.status_code == 200:
        log_admin_action(
            request.user.id,
            "UNBLOCK_USER",
            "user",
            user_id,
            f"{role} unblocked"
        )
        return Response({"message": "User unblocked"}, status=200)

    return Response({"error": "Failed to unblock user"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def verify_user(request):
    if not request.data.get('user_id') or not request.data.get('user_type'):
        return Response(
            {"error": "user_id and user_type are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = UserVerificationSerializer(data=request.data)

    if serializer.is_valid():
        obj = serializer.save(
            verified_by=request.user.id,
            verified_at=timezone.now()
        )
        log_admin_action(
            request.user.id,
            "VERIFY_USER",
            "user",
            obj.user_id,
            f"User {obj.user_type} verified"
        )
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def payment_disputes(request):
    if request.method == "GET":
        disputes = PaymentDispute.objects.all().order_by('-created_at')

        status_filter = request.query_params.get('status')
        search_query = request.query_params.get('search')
        user_id_filter = request.query_params.get('user_id')

        if status_filter:
            disputes = disputes.filter(status=status_filter)
        if user_id_filter:
            disputes = disputes.filter(Q(client_id=user_id_filter) | Q(freelancer_id=user_id_filter))
        if search_query:
            disputes = disputes.filter(
                Q(reason__icontains=search_query) |
                Q(payment_id__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        paginator = AdminPagination()
        paginated_disputes = paginator.paginate_queryset(disputes, request)
        serializer = PaymentDisputeSerializer(paginated_disputes, many=True)
        return paginator.get_paginated_response(serializer.data)

    required_fields = ['payment_id', 'client_id', 'freelancer_id', 'reason']
    if not all(request.data.get(field) for field in required_fields):
        return Response(
            {"error": f"Required fields: {', '.join(required_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = PaymentDisputeSerializer(data=request.data)

    if serializer.is_valid():
        dispute = serializer.save()
        log_admin_action(
            request.user.id,
            "PAYMENT_DISPUTE_CREATED",
            "payment",
            dispute.payment_id,
            f"Reason: {dispute.reason}"
        )
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdminUser])
def resolve_dispute(request, dispute_id):
    try:
        dispute = PaymentDispute.objects.get(id=dispute_id)
    except PaymentDispute.DoesNotExist:
        return Response(
            {"error": "Dispute not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    resolution = request.data.get('resolution')
    if not resolution:
        return Response(
            {"error": "resolution field is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    dispute.status = 'resolved'
    dispute.resolution = resolution
    dispute.resolved_at = timezone.now()
    dispute.resolved_by = request.user.id
    dispute.save()

    log_admin_action(
        request.user.id,
        "DISPUTE_RESOLVED",
        "payment",
        dispute.payment_id,
        f"Resolution: {resolution}"
    )

    serializer = PaymentDisputeSerializer(dispute)
    return Response(serializer.data, status=200)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_review(request, review_id):
    headers = {
        "Authorization": request.headers.get("Authorization")
    }
    try:
        response = requests.delete(
            f"http://review-service/api/reviews/delete/{review_id}",
            headers=headers,
            timeout=5
        )
    except requests.exceptions.RequestException:
        return Response(
            {"error": "Review service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if response.status_code == 200:
        log_admin_action(
            request.user.id,
            "DELETE_REVIEW",
            "review",
            review_id,
            "Review deleted by admin"
        )
        return Response({"message": "Review deleted"}, status=200)

    return Response({"error": "Failed to delete review"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def send_notification(request):
    user_id = request.data.get("user_id")
    notif_type = request.data.get("type")
    message = request.data.get("message")

    if not all([user_id, notif_type, message]):
        return Response(
            {"error": "user_id, type, and message are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = {
        "user_id": user_id,
        "type": notif_type,
        "message": message
    }
    headers = {
        "Authorization": request.headers.get("Authorization")
    }
    try:
        response = requests.post(
            "http://notification-service/api/notifications/send/",
            json=payload,
            headers=headers,
            timeout=5
        )
    except requests.exceptions.RequestException:
        return Response(
            {"error": "Notification service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if response.status_code == 201:
        log_admin_action(
            request.user.id,
            "SEND_NOTIFICATION",
            "user",
            user_id,
            f"Type: {notif_type}, Message: {message[:50]}"
        )
        return Response({"message": "Notification sent"}, status=200)

    return Response({"error": "Notification failed"}, status=502)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def view_all_notifications(request):
    headers = {
        "Authorization": request.headers.get("Authorization")
    }
    try:
        response = requests.get(
            "http://notification-service/api/notifications/view",
            headers=headers,
            timeout=5
        )
    except requests.exceptions.RequestException:
        return Response(
            {"error": "Notification service unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response(response.json(), status=response.status_code)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_logs(request):
    logs = AdminActionLog.objects.all().order_by("-created_at")

    action_filter = request.query_params.get('action')
    admin_id_filter = request.query_params.get('admin_id')
    target_type_filter = request.query_params.get('target_type')
    search_query = request.query_params.get('search')

    if action_filter:
        logs = logs.filter(action_type=action_filter)
    if admin_id_filter:
        logs = logs.filter(admin_id=admin_id_filter)
    if target_type_filter:
        logs = logs.filter(target_type=target_type_filter)
    if search_query:
        logs = logs.filter(
            Q(description__icontains=search_query) |
            Q(target_id__icontains=search_query) |
            Q(action_type__icontains=search_query)
        )

    paginator = AdminPagination()
    paginated_logs = paginator.paginate_queryset(logs, request)

    data = [
        {
            "id": log.id,
            "admin_id": log.admin_id,
            "action": log.action_type,
            "target": log.target_type,
            "target_id": log.target_id,
            "description": log.description,
            "time": log.created_at
        }
        for log in paginated_logs
    ]
    return paginator.get_paginated_response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_dispute_details(request, dispute_id):
    try:
        dispute = PaymentDispute.objects.get(id=dispute_id)
    except PaymentDispute.DoesNotExist:
        return Response(
            {"error": "Dispute not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = PaymentDisputeSerializer(dispute)
    return Response(serializer.data, status=200)