from django.shortcuts import render
from django.http import HttpResponse
from Kaldi_speech.models import EveryDayMotto,Course,Section,Sentence
import re
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

    pattern = r'\w+\'\w+|\w+-\w+|[\.\,\;\?\!\-\:\(\)\'\"]+|\w+'

    try:
        section_obj = Section.objects.get(id=section_id)

        course_obj = Course.objects.get(id=section_obj.course.id)

        objs = Sentence.objects.filter(section_id=section_id)

        # 例句数不为0
        if len(objs) != 0:
            sen_obj['sentenceInfo'] = []
            sen_obj['sectionInfo'] = {
                'id':section_id,
                'title':section_obj.title,
                'subtitle':section_obj.subtitle,
                'num_sentences':section_obj.num_sentences,
                'curr_sentence':objs[0].id
            }
            sen_obj['courseInfo'] = {
                'id':course_obj.id,
                'img':course_obj.course_img.url
            }

            for obj in objs:
                sep = []
                # 采用正则表达式对拆分英文单词，便于单词释义查询
                for i in re.finditer(pattern,obj.sentence_en):
                    sep.append(i.group())

                sen_obj['sentenceInfo'].append({
                    'id':obj.id,
                    'en':obj.sentence_en,
                    'ch':obj.sentence_ch,
                    'src':obj.sentence_src.url,
                    'en_sep':sep
                })
                
            sen_obj['error'] = 0
        else:
            sen_obj['error'] = 99

    except ValueError:
        sen_obj['error'] = 100
    
    return HttpResponse(json.dumps(sen_obj))

def updataStudyStatus(request):
    # 获取用户当前学习状况
    status = request.GET['curr_sentence']
    print('Study Status: {}'.format(status))
    return HttpResponse('服务器维护中，请稍后再试')

def getVerbTrans(request):
    verb = request.GET['verb']
    print('looking for verb: {}'.format(verb))
    return HttpResponse('试运行')

    