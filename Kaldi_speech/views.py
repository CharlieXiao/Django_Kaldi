from django.shortcuts import render
from django.http import HttpResponse
from Kaldi_speech.models import EveryDayMotto, Course, Section, Sentence, Verb, VerbExplain,User,UserCourse,UserVerb
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from YouDaoAPI.text_translation import getTrans
from YouDaoAPI.text2speech import getSpeech
from django.core.exceptions import ObjectDoesNotExist

import re
import json
import os
import requests
import datetime

request_url = 'http://127.0.0.1:8000'


# Create your views here.

def Index(request):

    open_id = request.GET['open_id']

    print('user open id : {}'.format(open_id))

    user_obj = User.objects.get(open_id=open_id)

    td = datetime.datetime.now()

    curr_date = datetime.date(td.year,td.month,td.day)

    # 计算用户学习天数
    learn_days = (curr_date-user_obj.add_time).days

    # 实际在首页还会显示用户学习天数等信息，点击开始学习直接进入上次未完成的课程，没有则直接进入课程列表
    # 获得每日格言
    motto = EveryDayMotto.objects.get(id=1)

    motto_obj = {
        'motto':motto.motto,
        'author':motto.author,
        'poster':request_url+motto.poster.url,
        'learn_days':learn_days,
    }

    return HttpResponse(json.dumps(motto_obj))

def getCourseInfo(requests):
    order = requests.GET['order']
    print('课程要求排列顺序为 ： {}'.format(order))
    if order == 'default':
        course_objs = Course.objects.all()
    elif order == 'heat':
        # 按照学习人数从大到小排序，需要反序
        course_objs = Course.objects.order_by('num_learners').reverse()
    elif order == 'new':
        # 按时间排序默认是按添加事件的先后，此处需要反序
        course_objs = Course.objects.order_by('add_time').reverse()

    courseInfo = []

    for obj in course_objs:
        # 遍历每一个课程，更新课程中章节信息
        obj.num_sections = len(obj.section_set.all())
        obj.save()

        courseInfo.append({
            'id':obj.id,
            'name':obj.name,
            'num_sections':obj.num_sections,
            'img':request_url+obj.course_img.url,
        })

    return HttpResponse(json.dumps(courseInfo))


def getSectionInfo(request):

    open_id = request.GET['open_id']

    course_id = request.GET['course_id']

    sec_obj = {}

    course_obj = Course.objects.get(id=course_id)

    section_objs = course_obj.section_set.all()

    user_obj = User.objects.get(open_id = open_id)

    # 获取当前用户学习情况
    try:
        uc_obj = UserCourse.objects.get(user=user_obj,course=course_obj)
        curr_section = uc_obj.curr_section
    except ObjectDoesNotExist:
        curr_section = section_objs[0].id

    # 动态更新课程中的章节数
    course_obj.num_sections = len(section_objs)

    course_obj.save()

    sec_obj['courseInfo'] = {
        'id': course_obj.id,
        'name': course_obj.name,
        'intro': course_obj.intro,
        'curr_section': curr_section,
        'sections': course_obj.num_sections,
        'img': course_obj.course_img.url
    }

    sec_obj['courseSec'] = []

    for sec in section_objs:
        sec_obj['courseSec'].append({
            'id': sec.id,
            'title': sec.title,
            'subtitle': sec.subtitle
        })

    return HttpResponse(json.dumps(sec_obj))


def getSentenceInfo(request):

    section_id = int(request.GET['section_id'])

    # 获取用户open_id，修改相关信息
    open_id = request.GET['open_id']

    # print('section_id = {}'.format(section_id))

    sen_obj = {}

    pattern = r'\w+\'\w+|\w+-\w+|[\.\,\;\?\!\-\:\(\)\'\"]+|\w+'

    user_obj = User.objects.get(open_id=open_id)

    section_obj = Section.objects.get(id=section_id)

    course_obj = Course.objects.get(id=section_obj.course.id)

    objs = section_obj.sentence_set.all()

    # 需要动态更新 num_sentences 的值

    # print(len(objs))

    section_obj.num_sentences = len(objs)

    section_obj.save()

    # 例句数不为0
    if len(objs) != 0:
        curr_sentence = objs[0].id
        # 更新用户数据和用户课程数据库
        try:
            uc_obj = UserCourse.objects.get(user=user_obj,course=course_obj)
            # 此处section_id是字符串类型的，而uc_obj.curr_section是整型，因而不相等
            if uc_obj.curr_section == section_id:
                curr_sentence = uc_obj.curr_sentence
            else:
                uc_obj.curr_section = section_id
                uc_obj.curr_sentence = curr_sentence
                uc_obj.save()
        except ObjectDoesNotExist:
            uc_obj = uc.objects.create(user=user_obj,course=course_obj,curr_section=section_id,curr_sentence=curr_sentence)

        #更新当前课程
        user_obj.curr_course = course_obj.id

        user_obj.save()

        sen_obj['sentenceInfo'] = {}
        sen_obj['sectionInfo'] = {
            'id': section_id,
            'title': section_obj.title,
            'subtitle': section_obj.subtitle,
            'num_sentences': section_obj.num_sentences,
            'curr_sentence': curr_sentence
        }
        sen_obj['courseInfo'] = {
            'id': course_obj.id,
            'img': course_obj.course_img.url
        }

        # 排序序号

        index = 1

        for obj in objs:
                
            # print(obj.sentence_src)
            # 如果是默认录音，则连接有道进行更新
            if obj.sentence_src == 'default/default.wav':
                # 尝试从有道获取句子发音
                raw_data = json.loads(getSpeech(obj.sentence_en))
                # 如果error的值不为0，代表请求出错，则仍然试使用原来的数据
                errorCode = raw_data['errorCode']
                if errorCode == '0':
                    # 数据获取成功
                    audio_url = raw_data['speakUrl']
                    audio_file = ContentFile(requests.get(audio_url).content)
                    obj.sentence_src.save(str(obj.id)+'.mp3',audio_file)
                    # uk_file = ContentFile(requests.get(uk_url).content)
                    # verbObj.uk_speech.save(verb+'_uk.mp3', uk_file)
                    # print(audio_url)

            sep = []
            # 采用正则表达式对拆分英文单词，便于单词释义查询
            for i in re.finditer(pattern, obj.sentence_en):
                sep.append(i.group())

            sen_obj['sentenceInfo'][obj.id] = {
                'index': index,
                'en': obj.sentence_en,
                'ch': obj.sentence_ch,
                'src': obj.sentence_src.url,
                'en_sep': sep
            }

            index += 1
                
        sen_obj['error'] = 0
    else:
        sen_obj['error'] = 99

    # print(sen_obj)

    return HttpResponse(json.dumps(sen_obj))

def userLogin(request):
    WX_URL = 'https://api.weixin.qq.com/sns/jscode2session'
    APP_SECRECT = 'b1ee7e749ce757a9831dd942ac7e5730'
    APP_ID = 'wx28edbe6419ec7914'
    code = request.GET['code']
    data = {
        'appid':APP_ID,
        'secret':APP_SECRECT,
        'js_code':code,
        'grant_type':'authorization_code'
    }

    res = json.loads(requests.get(WX_URL,params=data).content)

    print(res)

    open_id = res['openid']

    # get_or_create返回的是一个元组
    user_obj = User.objects.get_or_create(open_id=open_id)

    # 返回open_id,并在小程序中存储在本地

    data = {
        'open_id':open_id,
    }

    return HttpResponse(json.dumps(data))

def updataStudyStatus(request):
    # 获取用户当前学习状况
    open_id = request.GET['open_id']
    
    up_type = request.GET['type']

    user_obj = User.objects.get(open_id=open_id)

    if up_type == '1':
        curr_sentence = request.GET['curr_sentence']
        uc_obj = UserCourse.objects.get(user=user_obj,course=user_obj.curr_course) 
        print(uc_obj)
        uc_obj.curr_sentence = curr_sentence
        uc_obj.save()
        return HttpResponse('更新成功')

    return HttpResponse('服务器维护中')


def getVerbTrans(request):

    pattern = r'(\w{1,10}\.)\s(.*)'

    verb = request.GET['verb'].lower()

    open_id = request.GET['open_id']

    user_obj = User.objects.get(open_id=open_id)

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

    # 查询用户是否收藏过单词
    try:
        uv_obj = UserVerb.objects.get(user=user_obj,verb=verbObj)
        isFav = True
        print('用户收藏过这个单词了嗷')
    except ObjectDoesNotExist:
        isFav = False
        print('用户没收藏过这个单词嗷')

    verbData = {
        'verb':verbObj.verb,
        'uk-phonetic':verbObj.uk_phonetic,
        'us-phonetic':verbObj.us_phonetic,
        'uk-speech':verbObj.uk_speech.url,
        'us-speech':verbObj.us_speech.url,
        'explains':[],
        'isFav': isFav
    }

    for i in verbObj.verbexplain_set.all():
        verbData['explains'].append({
            'pos':i.pos,
            'explain':i.explain
        })

    # print(verbData)

    return HttpResponse(json.dumps(verbData))

def addVerbFav(request):
    open_id = request.GET['open_id']
    isFav = request.GET['isFav']
    verb = request.GET['verb']

    user_obj = User.objects.get(open_id=open_id)

    verb_obj = Verb.objects.get(verb=verb)

    if isFav == 'true':
        # 用户取消收藏
        uv_obj = UserVerb.objects.get(user=user_obj,verb=verb_obj)
        uv_obj.delete()

    else:
        # 用户添加收藏
        UserVerb.objects.create(user=user_obj,verb=verb_obj)

    return HttpResponse('处理成功')

def getVerbList(request):
    return HttpResponse('数据处理中')