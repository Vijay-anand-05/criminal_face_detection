from django.urls import path
from . import views

urlpatterns = [
    path('', views.detection_page, name='detection_page'),
path('camera-scan/', views.camera_scan, name='camera_scan'),
 path('video_feed/', views.video_feed, name='video_feed'),

 path('start_camera/', views.start_camera, name='start_camera'),
    path('stop_camera/', views.stop_camera, name='stop_camera'),

    path('add_criminal/', views.add_criminal, name='add_criminal'),
    path('delete_criminal/<int:criminal_id>/', views.delete_criminal, name='delete_criminal'),
# path('add_image/', views.add_image, name='add_image'),
]
