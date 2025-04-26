from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import *
from .serializers import *
import requests

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['is_superuser'] = user.is_superuser
        token['is_staff'] = user.is_staff
        # token['groups'] = user.groups.all()
        token['username'] = user.username
        token['role'] = user.role
        
        if user.role == 'DOCTOR' and hasattr(user, 'doctor_profile'):
            token['profile_id'] = user.doctor_profile.id
        elif user.role == 'PATIENT' and hasattr(user, 'patient_profile'):
            token['profile_id'] = user.patient_profile.id
        else:
            token['profile_id'] = None
        # ...

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# Sign up
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Account Created Successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Login
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#Logout
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    # Return users based on roles
    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return User.objects.all()
        elif user.role == User.Role.DOCTOR:
            return User.objects.filter(role=User.Role.DOCTOR)
        return User.objects.filter(id=user.id)  # Patients see only themselves

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('created_by').prefetch_related('assigned_to')
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Managers only:
        if self.request.user.role != 'manager':
            raise permissions.PermissionDenied("Only managers can assign tasks.")
        task = serializer.save(created_by=self.request.user)

        # Notify assigned users
        for user in task.assigned_to.all():
            Notification.objects.create(
                recipient=user,
                message=f"You were assigned to task: {task.title}",
                url=f"/tasks/{task.id}/"
            )
            self.send_socket_event(user.id, f"New task assigned: {task.title}")

    def send_socket_event(self, user_id, message):
        # Call your Node.js server API
        try:
            requests.post('http://localhost:4000/notify', json={
                'userId': user_id,
                'message': message
            })
        except:
            pass  # Don't block on failure

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('task', 'author').prefetch_related('mentions')
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)

        # Notify mentioned users
        for user in comment.mentions.all():
            Notification.objects.create(
                recipient=user,
                message=f"You were mentioned in a comment on task: {comment.task.title}",
                url=f"/tasks/{comment.task.id}/"
            )
            self.send_socket_event(user.id, f"You were mentioned in: {comment.task.title}")

    def send_socket_event(self, user_id, message):
        try:
            requests.post('http://localhost:4000/notify', json={
                'userId': user_id,
                'message': message
            })
        except:
            pass

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"status": "all notifications marked as read"})
