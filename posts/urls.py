from django.urls import path
from . import views

urlpatterns = [
    path('', views.PostListCreateAPIView.as_view(), name='post-list-create'),
    path('<uuid:id>/', views.PostRetrieveUpdateDestroyAPIView.as_view(), name='post-detail'),
    path('<uuid:id>/comments/', views.CommentListCreateAPIView.as_view(), name='post-comments'),
    path('<uuid:post_id>/comments/<uuid:comment_id>/', views.CommentRetrieveAPIView.as_view(), name='comment-retrieve'),
    path('<uuid:post_id>/comments/<uuid:comment_id>/likes/', views.CommentLikesListCreateDestroyAPIView.as_view(), name='comment-likes'),
    path('<uuid:id>/likes/', views.PostLikeListCreateDestroyAPIView.as_view(), name='post-like'),
]