'''
@Descripttion: 
@version: 
@Author: Paul
@Date: 2019-08-29 22:59:21
@LastEditors: Paul
@LastEditTime: 2020-04-08 00:46:00
'''
"""Django_Kaldi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
import Kaldi_speech.views as ks_views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('index/', ks_views.Index),
    path('CourseInfo/', ks_views.getCourseInfo),
    path('SectionInfo/', ks_views.getSectionInfo),
    path('SentenceInfo/', ks_views.getSentenceInfo),
    path('VerbTrans/', ks_views.getVerbTrans),
    path('updateStudyStatus/', ks_views.updataStudyStatus),
    path('addVerbFav/', ks_views.addVerbFav),
    path('VerbList/', ks_views.getVerbList),
    path('removeVerbList/', ks_views.removeVerbList),
    path('judgeAudio/', ks_views.judgeAudio),
    path('AudioList/', ks_views.getAudioList),
    path('removeAudioList/', ks_views.removeAudioList),
    path('UserCourse/', ks_views.getUserCourse),
    path('UserCalendar/', ks_views.getUserCalendar),

    path('Test/', ks_views.TestFunction),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
