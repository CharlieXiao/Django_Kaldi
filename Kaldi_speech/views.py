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

    sec_obj = {}

    try:
        course_obj = Course.objects.get(id=course_id)

        section_objs = Section.objects.filter(course_id=course_id)

        sec_obj['courseInfo'] = {
            'id':course_obj.id,
            'name':course_obj.name,
            'intro':course_obj.intro,
            'curr_section':section_objs[0].id,
            'sections':course_obj.num_sections,
            'img':course_obj.course_img.url
        }

        sec_obj['courseSec'] = []

        for sec in section_objs:
            print(sec)
            temp = {
                'id':sec.id,
                'title':sec.title,
                'subtitle':sec.subtitle
            }
            sec_obj['courseSec'].append(temp)

        sec_obj['error'] = 0

    except ValueError:
        sec_obj['error'] = 100

    return HttpResponse(json.dumps(sec_obj))
    
def getSentenceInfo(request):
    section_id = request.GET['section_id']

    print('section_id = {}'.format(section_id))

    sen_obj = {}

    try:
        section_obj = Section.objects.get(id=section_id)

        course_obj = Course.objects.get(id=section_obj.course.id)

        objs = Sentence.objects.filter(section_id=section_id)

        # 例句数不为0
        if len(objs) != 0:
            sen_obj['sentence_en'] = []
            sen_obj['sentence_ch'] = []
            sen_obj['sentionInfo'] = {
                'id':section_id,
                'title':section_obj.title,
                'subtitle':section_obj.subtitle,
                'num_sentences':section_obj.num_sentences,
                'curr_sentence':objs[0].id
            }
            sen_obj['courseImage'] = course_obj.course_img.url

            for obj in objs:
                sen_obj['sentence_en'].append(obj.sentence_en)
                sen_obj['sentence_ch'].append(obj.sentence_ch)

            sen_obj['error'] = 0
        else:
            sen_obj['error'] = 99


    except ValueError:
        sen_obj['error'] = 100
    
    return HttpResponse(json.dumps(sen_obj))

    