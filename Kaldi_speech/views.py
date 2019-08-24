from django.shortcuts import render
from django.http import HttpResponse
from Kaldi_speech.models import EveryDayMotto,Course,Section,Sentence

import json

# Create your views here.

def Index(request):
    #实际在首页还会显示用户学习天数等信息，点击开始学习直接进入上次未完成的课程，没有则直接进入课程列表
    #获得每日格言
    motto = EveryDayMotto.objects.get(id=1)
    host = request.get_host()
    print('http://'+request.get_host()+motto.poster.url)
    motto_obj = {}
    motto_obj['motto'] = motto.motto
    motto_obj['author'] = motto.author
    motto_obj['poster'] = 'http://'+request.get_host()+motto.poster.url
    return HttpResponse(json.dumps(motto_obj))

def getSectionInfo(request):
    course_id = request.GET['course_id']

    course_obj = Course.objects.get(id=course_id)

    section_objs = Section.objects.filter(course_id=course_id)

    sec_obj = {}

    sec_obj['courseInfo'] = {
        'id':course_obj.id,
        'name':course_obj.name,
        'intro':course_obj.intro,
        'curr_section':1,
        'sections':course_obj.num_sections,
        'img':course_obj.course_img.url
    }

    sec_obj['courseSec'] = []

    start_id = section_objs[0].id-1

    for sec in section_objs:
        print(sec)
        temp = {
            'id':sec.id-start_id,
            'title':sec.title,
            'subtitle':sec.subtitle
        }
        sec_obj['courseSec'].append(temp)

    return HttpResponse(json.dumps(sec_obj))