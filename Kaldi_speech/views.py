from django.shortcuts import render
from django.http import HttpResponse
from Kaldi_speech.models import EveryDayMotto, Course, Section, Sentence, Verb, VerbExplain
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from YouDaoAPI.text_translation import getTrans
from django.core.exceptions import ObjectDoesNotExist

import re
import json
import os
import requests


# Create your views here.

def Index(request):
    # 实际在首页还会显示用户学习天数等信息，点击开始学习直接进入上次未完成的课程，没有则直接进入课程列表
    # 获得每日格言
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
            'id': course_obj.id,
            'name': course_obj.name,
            'intro': course_obj.intro,
            'curr_section': section_objs[0].id,
            'sections': course_obj.num_sections,
            'img': course_obj.course_img.url
        }

        sec_obj['courseSec'] = []

        for sec in section_objs:
            print(sec)
            temp = {
                'id': sec.id,
                'title': sec.title,
                'subtitle': sec.subtitle
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
                'id': section_id,
                'title': section_obj.title,
                'subtitle': section_obj.subtitle,
                'num_sentences': section_obj.num_sentences,
                'curr_sentence': objs[0].id
            }
            sen_obj['courseInfo'] = {
                'id': course_obj.id,
                'img': course_obj.course_img.url
            }

            for obj in objs:
                sep = []
                # 采用正则表达式对拆分英文单词，便于单词释义查询
                for i in re.finditer(pattern, obj.sentence_en):
                    sep.append(i.group())

                sen_obj['sentenceInfo'].append({
                    'id': obj.id,
                    'en': obj.sentence_en,
                    'ch': obj.sentence_ch,
                    'src': obj.sentence_src.url,
                    'en_sep': sep
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

    pattern = r'(\w{1,10}\.)\s(.*)'

    verb = request.GET['verb'].lower()

    print('looking for verb: {}'.format(verb))

    try:
        # 尝试从数据库中获取单词信息
        verbObj = Verb.objects.get(verb=verb)
        print('数据库中已经存在了嗷')
    except ObjectDoesNotExist:
        # 获取不到则调用有道查词API获取单词释义，并添加到数据库中
        verbInfo = json.loads(getTrans(verb))
        raw_explains = verbInfo['basic']['explains']
        # 查询结果中，可能会出现音标不存在的情况
        # 应该先优先尝试获取
        try:
            uk_phonetic = verbInfo['basic']['uk-phonetic']
        except KeyError:
            uk_phonetic = ""
        try:
            us_phonetic = verbInfo['basic']['us-phonetic']
        except KeyError:
            us_phonetic = ""

        verbObj = Verb.objects.create(
            verb=verb,
            uk_phonetic=uk_phonetic,
            us_phonetic=us_phonetic,
        )

        # # 下载对应单词的发音

        uk_url = verbInfo['basic']['uk-speech']
        # 如果对应链接为空，则无法发音
        # if uk_url == "":
        uk_file = ContentFile(requests.get(uk_url).content)
        verbObj.uk_speech.save(verb+'_uk.mp3', uk_file)

        us_url = verbInfo['basic']['us-speech']
        us_file = ContentFile(requests.get(us_url).content)
        verbObj.us_speech.save(verb+'_us.mp3', us_file)
        
        # 同样还有可能出现链接为空的情况，暂时未做处理

        for explain in raw_explains:
            e = re.match(pattern,explain)
            if e != None:
                VerbExplain.objects.create(
                    verb=verbObj,
                    pos=e[1],
                    explain=e[2]
                )
            else:
                # 如果释义中不存在词性属性时，不添加词性
                VerbExplain.objects.create(
                    verb=verbObj,
                    pos="",
                    explain=explain
                )

    verbData = {
        'verb':verbObj.verb,
        'uk-phonetic':verbObj.uk_phonetic,
        'us-phonetic':verbObj.us_phonetic,
        'uk-speech':verbObj.uk_speech.url,
        'us-speech':verbObj.us_speech.url,
        'explains':[]
    }

    for i in verbObj.verbexplain_set.all():
        verbData['explains'].append({
            'pos':i.pos,
            'explain':i.explain
        })

    # print(verbData)

    return HttpResponse(json.dumps(verbData))
