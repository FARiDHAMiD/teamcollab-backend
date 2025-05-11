from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.parsers import MultiPartParser, FormParser
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

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            return User.objects.all()
        elif user.role == 'developer':
            return User.objects.filter(role='developer')
        elif user.role == 'tester':
            return User.objects.filter(role='tester')
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'], url_path='developers-testers')
    def list_users(self, request):
        qs = User.objects.filter(role__in=['developer', 'tester'])
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('created_by').select_related('assigned_to')
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            # Managers see all tasks
            return Task.objects.all()
        else:
            # Developers and testers see only tasks assigned to them
            return Task.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        if self.request.user.role != 'manager':
            raise permissions.PermissionDenied("Only managers can assign tasks.")
        task = serializer.save(created_by=self.request.user)

        # No `.all()` needed for ForeignKey, just use `task.assigned_to`
        Notification.objects.create(
            recipient=task.assigned_to,
            message=f"You were assigned to task: {task.title}",
            url=f"/tasks/{task.id}/"
        )
        self.send_socket_event(task.assigned_to.id, f"New task assigned: {task.title}")

    def send_socket_event(self, user_id, message):
        try:
            requests.post('http://localhost:4000/notify', json={
                'userId': user_id,
                'message': message
            })
        except:
            pass

    @action(detail=True, methods=['get'], url_path='user-tasks')
    def user_tasks(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        tasks = Task.objects.filter(assigned_to=user)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Comment.objects.select_related('task', 'author').prefetch_related('mentions')
        task_id = self.request.query_params.get('task_id')
        if task_id:
            queryset = queryset.filter(task__id=task_id)
        return queryset

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
