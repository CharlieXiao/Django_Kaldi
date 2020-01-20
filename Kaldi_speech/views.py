from django.shortcuts import render
from django.http import HttpResponse
from Kaldi_speech.models import EveryDayMotto, Course, Section, Sentence, Verb, VerbExplain, User, UserCourse, UserVerb, UserSentence , UserSection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from YouDaoAPI.text_translation import getTrans
from YouDaoAPI.text2speech import getSpeech
from django.core.exceptions import ObjectDoesNotExist
from Score.score import get_score
from Django_Kaldi.settings import MEDIA_ROOT

import re
import json
import os
import requests
import datetime

# Create your views here.
GOP_ROOT = '/home/ubuntu/kaldi/egs/gop-compute'

def Index(request):

    motto_obj = None

    try:
        open_id = request.GET['open_id']

        # print('user open id : {}'.format(open_id))

        user_obj = User.objects.get(open_id=open_id)

        # 计算用户学习天数
        td = datetime.datetime.now()
        curr_date = datetime.date(td.year, td.month, td.day)
        # 只要用户点进小程序，即算学习一天
        # 获取当前时间，比对，不相同则learn-days加一天
        # 比较最后学习时间，如果不在同一天，则不修改
        if curr_date != user_obj.last_learn_time:
            print('更新用户学习天数')
            user_obj.learn_days += 1
        user_obj.save()

        # 实际在首页还会显示用户学习天数等信息，点击开始学习直接进入上次未完成的课程，没有则直接进入课程列表
        # 获得每日格言
        motto = EveryDayMotto.objects.all()[0]

        motto_obj = {
            'motto': motto.motto,
            'author': motto.author,
            'poster': motto.poster.url,
            'learn_days': user_obj.learn_days,
            'curr_course':user_obj.curr_course,
        }
    except:
        motto_obj = {
            'error':400
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

        courseInfo.append({
            'id': obj.id,
            'name': obj.name,
            'num_sections': len(obj.section_set.all()),
            'img': obj.course_img.url,
        })

    return HttpResponse(json.dumps(courseInfo))


def getSectionInfo(request):

    open_id = request.GET['open_id']

    course_id = request.GET['course_id']

    sec_obj = {}

    course_obj = Course.objects.get(id=course_id)

    section_objs = course_obj.section_set.all()

    user_obj = User.objects.get(open_id=open_id)

    # 更新当前课程
    user_obj.curr_course = course_obj.id
    user_obj.save()
    

    # 获取当前用户学习情况
    try:
        uc_obj = UserCourse.objects.get(user=user_obj, course=course_obj)
        curr_section = uc_obj.curr_section
    except ObjectDoesNotExist:
        curr_section = section_objs[0].id
        # 添加学习记录
        uc_obj = UserCourse.objects.create(user=user_obj,course=course_obj,curr_section=curr_section)

    sec_obj['courseInfo'] = {
        'id': course_obj.id,
        'name': course_obj.name,
        'intro': course_obj.intro,
        'curr_section': curr_section,
        'sections': len(section_objs),
        'img': course_obj.course_img.url
    }

    sec_obj['courseSec'] = []

    sec_obj['section_finish'] = []

    prev_finish = True

    for sec in section_objs:
        # 获取用户完成状况
        try:
            us_obj = UserSection.objects.get(user=user_obj,section=sec)
            is_finish = us_obj.is_finish
        except ObjectDoesNotExist:
            is_finish = False
        

        sec_obj['courseSec'].append({
            'id': sec.id,
            'title': sec.title,
            'subtitle': sec.subtitle,
        })

        sec_obj['section_finish'].append(is_finish)
        

    return HttpResponse(json.dumps(sec_obj))

def getSentenceInfo(request):

    section_id = int(request.GET['section_id'])

    # 获取用户open_id，修改相关信息
    open_id = request.GET['open_id']

    # print('section_id = {}'.format(section_id))

    sen_obj = {}

    # pattern = r'\w+\'\w+|\w+-\w+|[\.\,\;\?\!\-\:\(\)\'\"]+|\w+'

    user_obj = User.objects.get(open_id=open_id)

    section_obj = Section.objects.get(id=section_id)

    course_obj = Course.objects.get(id=section_obj.course.id)

    objs = section_obj.sentence_set.all()

    # 更新当前章节
    uc_obj = UserCourse.objects.get(user=user_obj,course=course_obj)
    uc_obj.curr_section = section_obj.id
    uc_obj.save()

    # 例句数不为0
    if len(objs) != 0:
        curr_sentence = objs[0].id
        # 更新用户数据和用户课程数据库
        try:
            us_obj = UserSection.objects.get(user=user_obj,section=section_obj)
            curr_sentence = us_obj.curr_sentence
        except ObjectDoesNotExist:
            us_obj = UserSection.objects.create(
                user=user_obj, section=section_obj,curr_sentence=curr_sentence)

        sen_obj['sentenceInfo'] = {}
        sen_obj['sectionInfo'] = {
            'id': section_id,
            'title': section_obj.title,
            'subtitle': section_obj.subtitle,
            'num_sentences': len(objs),
            'curr_sentence': curr_sentence
        }
        sen_obj['courseInfo'] = {
            'id': course_obj.id,
            'img': course_obj.course_img.url
        }

        # 排序序号

        index = 1

        for obj in objs:
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
                    obj.sentence_src.save(str(obj.id)+'.mp3', audio_file)
                    # uk_file = ContentFile(requests.get(uk_url).content)
                    # verbObj.uk_speech.save(verb+'_uk.mp3', uk_file)
                    # print(audio_url)

            # sep = []
            # 采用正则表达式对拆分英文单词，便于单词释义查询
            # for i in re.finditer(pattern, obj.sentence_en):
            #     sep.append(i.group())
            sep = []
            # 此处需要使用正则表达式筛选单词
            for verb in re.findall('[~`!@#$%^&*()_\-+={}\[\]\|\\:;"\'<,.>?/]+|[A-Za-z\']+',obj.sentence_en):
                sep.append({
                    'verb':verb,
                    'isBad':False
                })

            print(sep)

            # sep = json.load(open("C:\\Users\\mayn\\Documents\\Django_Kaldi\\test.json",'r',encoding='utf-8'))['sentence']

            # 判断用户是否有历史录音
            try:
                us_obj = UserSentence.objects.get(user=user_obj, sentence=obj)
                hasJudge = 1
                score = us_obj.score
                user_src = us_obj.audio.url
            except ObjectDoesNotExist:
                hasJudge = 0
                score = 0
                user_src = ''

            # 需要返回用户历史评分结果和音频url

            sen_obj['sentenceInfo'][obj.id] = {
                'index': index,
                'en': obj.sentence_en,
                'ch': obj.sentence_ch,
                'src': obj.sentence_src.url,
                'en_sep': sep,
                'score': score,
                'user-src': user_src,
                'hasJudge': hasJudge,
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
        'appid': APP_ID,
        'secret': APP_SECRECT,
        'js_code': code,
        'grant_type': 'authorization_code'
    }

    res = json.loads(requests.get(WX_URL, params=data).content)

    print(res)

    open_id = res['openid']

    # get_or_create返回的是一个元组
    user_obj = User.objects.get_or_create(open_id=open_id)

    # 返回open_id,并在小程序中存储在本地

    data = {
        'open_id': open_id,
    }

    return HttpResponse(json.dumps(data))


def updataStudyStatus(request):
    # 获取用户当前学习状况
    open_id = request.GET['open_id']

    up_type = request.GET['type']

    user_obj = User.objects.get(open_id=open_id)

    if up_type == '1':
        curr_sentence = request.GET['curr_sentence']
        sen_obj = Sentence.objects.get(id=curr_sentence)
        sec_obj = sen_obj.section
        us_obj = UserSection.objects.get(
            user=user_obj, section=sec_obj)
        # 可以在此处遍历该章节下所有句子，判断是否完成这一章节
        sec_finish = True
        for sen in sec_obj.sentence_set.all():
            try:
                UserSentence.objects.get(user=user_obj,sentence=sen)
            except ObjectDoesNotExist:
                sec_finish = False
                break
        us_obj.curr_sentence = curr_sentence
        if sec_finish:
            us_obj.is_finish = sec_finish
        us_obj.save()
        # 还需要遍历该课程下所有章节，判断这一课程是否完成
        course_obj = sec_obj.course
        course_finish = True
        uc_obj = UserCourse.objects.get(user=user_obj,course=course_obj)
        sec_objs = course_obj.section_set.all()

        section_finish = []

        for sec in sec_objs:
            try:
                temp_obj = UserSection.objects.get(user=user_obj,section=sec)
                section_finish.append(temp_obj.is_finish)
                if not temp_obj.is_finish:
                    course_finish = False
            except ObjectDoesNotExist:
                section_finish.append(False)
                course_finish = False
        if course_finish:
            uc_obj.is_finish = course_finish
            # 需要修正curr_course
            uc_obj.save()
        # 返回对应课程完成信息
        return HttpResponse(json.dumps(section_finish))

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
            e = re.match(pattern, explain)
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
        uv_obj = UserVerb.objects.get(user=user_obj, verb=verbObj)
        isFav = True
        print('用户收藏过这个单词了嗷')
    except ObjectDoesNotExist:
        isFav = False
        print('用户没收藏过这个单词嗷')

    verbData = {
        'verb': verbObj.verb,
        'verb_id': verbObj.id,
        'uk-phonetic': verbObj.uk_phonetic,
        'us-phonetic': verbObj.us_phonetic,
        'uk-speech': verbObj.uk_speech.url,
        'us-speech': verbObj.us_speech.url,
        'explains': [],
        'isFav': isFav
    }

    for i in verbObj.verbexplain_set.all():
        verbData['explains'].append({
            'pos': i.pos,
            'explain': i.explain
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
        uv_obj = UserVerb.objects.get(user=user_obj, verb=verb_obj)
        uv_obj.delete()

    else:
        # 用户添加收藏
        UserVerb.objects.create(user=user_obj, verb=verb_obj)

    return HttpResponse('处理成功')


def getVerbList(request):
    open_id = request.GET['open_id']

    user_obj = User.objects.get(open_id=open_id)

    vb_objs = user_obj.userverb_set.all()

    res_obj = {}

    # 判断用户是否有收藏过单词
    if len(vb_objs) == 0:
        res_obj['hasVerb'] = False
    else:
        print('用户有收藏过单词嗷')

        res_obj['hasVerb'] = True

        res_obj['verbList'] = []

        for obj in vb_objs:
            temp_verb = obj.verb

            # 对于explain需要用正则表达式获取其第一个解释的第一个

            explain = temp_verb.verbexplain_set.all()[0]

            temp_obj = {
                'verb': temp_verb.verb,
                'id': obj.id,
                'phonetic': temp_verb.us_phonetic,
                'trans': {
                    'pos': explain.pos,
                    'explain': explain.explain.split('；')[0]
                },
                'speech': temp_verb.us_speech.url,
                'notRemove': True,
            }

            res_obj['verbList'].append(temp_obj)

    return HttpResponse(json.dumps(res_obj))


def removeVerbList(request):
    removeList = json.loads(request.GET['removeList'])

    for verb in removeList:
        temp_obj = UserVerb.objects.get(id=verb)
        temp_obj.delete()

    return HttpResponse('处理成功')


def judgeAudio(request):
    if request.method == 'POST':
        # 必须是post请求
        # print(request.POST)
        # 使用DJango作为微信小程序后端，需要禁用Django的CSRF cookie监测
        open_id = request.POST['open_id']
        judge_type = request.POST['type']
        print('Type: {}'.format(judge_type))
        # 采用read直接读取二进制文件，对于较大文件不便使用，但此处用户录音一般不超过一分钟，可以使用
        # 尝试直接保存用户发音
        # user_audio = ContentFile(request.FILES['audio'].read())
        user_audio = request.FILES['audio'].read()
        print('audio file size:{}'.format(len(user_audio)))
        user_obj = User.objects.get(open_id=open_id)

        score = 0
        user_audio_src = ''
        # 分为两种评分形式，对单词评分和对句子评分
        if judge_type == 'verb':
            # score = getScore()
            # try save audio file
            verb_id = int(request.POST['verb_id'])
            verb_obj = Verb.objects.get(id=verb_id)
            
            audio_file_path = os.path.join(MEDIA_ROOT,'temp','temp_verb.mp3')
            # 这里收到的文件大小为0，有问题
            print('audio file size: {}'.format(len(user_audio)))
            with open(audio_file_path,'wb') as audio_file:
                audio_file.write(user_audio)
            audio_file.close()
            
            res = get_score(GOP_ROOT,'temp_verb',audio_file_path,verb_obj.verb.upper())

            if res == -1:
                return HttpResponse(json.dumps({'error_code':50}))
            res['error_code'] = 0

        else:
            sentence_id = int(request.POST['sentence_id'])
            sentence_obj = Sentence.objects.get(id=sentence_id)
            try:
                ua_obj = UserSentence.objects.get(
                    user=user_obj, sentence=sentence_obj)
                # 删除过去的发音，并替换
                temp_path = ua_obj.audio.path
                ua_obj.audio.delete()
                # 最好是将原来的发音清除
                # os.system('rm {}'.format(temp_path))
                ua_obj.audio.save('{}_{}.mp3'.format(
                    user_obj.id, sentence_id), ContentFile(user_audio))
                print('用户以前发音过')
            except ObjectDoesNotExist:
                print('用户第一次发音')
                ua_obj = UserSentence.objects.create(
                    user=user_obj, sentence=sentence_obj, score=score)
                ua_obj.audio.save('{}_{}.mp3'.format(
                    user_obj.id, sentence_id), ContentFile(user_audio))

            user_audio_src = ua_obj.audio.url
            FileName = '{}_{}'.format(user_obj.id,sentence_id)
            # 需要提前对例句进行处理，去除所有标点符号
            # 建议在添加例句时就对例句进行处理
            # 添加一个数据像：sentence_en_upper
            # 但添加时就对数据进行处理
            if sentence_obj.sentence_upper == '@default':
                # 对例句进行处理，去除标点并转为大写
                print(sentence_obj.sentence_en)
                verb_list = re.findall('[A-Za-z\']+',sentence_obj.sentence_en)
                sentence_upper = ' '.join(verb_list)
                sentence_obj.sentence_upper = sentence_upper.upper()
                sentence_obj.save()
            print(sentence_obj.sentence_upper)
            res = get_score(GOP_ROOT,FileName,ua_obj.audio.path,sentence_obj.sentence_upper)
            # res = -1
            if res == -1:
                return HttpResponse(json.dumps({'error_code':50}))
            ua_obj.score = res['score']
            ua_obj.save()
            res['user-audio']= user_audio_src
            res['error_code'] = 0

        return HttpResponse(json.dumps(res))
    else:
        return HttpResponse(json.dumps({'error_code':99}))


def getAudioList(request):
    open_id = request.GET['open_id']

    user_obj = User.objects.get(open_id=open_id)

    va_objs = user_obj.usersentence_set.all()

    res_obj = {}

    # 判断用户是否有过录音
    if len(va_objs) == 0:
        res_obj['hasAudio'] = False
    else:
        print('用户有录音嗷')

        res_obj['hasAudio'] = True

        res_obj['AudioList'] = []

        for obj in va_objs:

            temp_obj = {
                'id': obj.id,
                'sentence_en': obj.sentence.sentence_en,
                'src': obj.audio.url,
                'score': obj.score,
                'course': obj.sentence.section.course.name,
                'notRemove': True,
            }

            res_obj['AudioList'].append(temp_obj)

    # print(res_obj)

    return HttpResponse(json.dumps(res_obj))


def removeAudioList(request):
    removeList = json.loads(request.GET['removeList'])

    for sentence in removeList:
        temp_obj = UserSentence.objects.get(id=sentence)
        temp_obj.delete()

    return HttpResponse('处理成功')

# 是否需要在数据库中记录是否学习完成，章节是否学习完成，如此较好判别是否学习完成

def getUserCourse(request):
    open_id = request.GET['open_id']
    order = request.GET['order']

    user_obj = User.objects.get(open_id=open_id)

    if order == '1':
        course_objs = UserCourse.objects.filter(user=user_obj)
    elif order == '2':
        # 已经完成的课程
        course_objs = UserCourse.objects.filter(user=user_obj,is_finish = False)
    elif order == '3':
        # 未完成的课程
        course_objs = UserCourse.objects.filter(user=user_obj,is_finish = True)

    courseInfo = []

    for uc_obj in course_objs:
        section_set = uc_obj.course.section_set.all()
        num_finish = 0
        if uc_obj.is_finish:
            num_finish = len(section_set)
        else:
            for sec in section_set:
                if uc_obj.curr_section != sec.id:
                    num_finish += 1
                else:
                    break
        
        courseInfo.append({
            'id':uc_obj.course.id,
            'name':uc_obj.course.name,
            'img':uc_obj.course.course_img.url,
            'curr':num_finish,
            'total':len(section_set),
        })

    return HttpResponse(json.dumps(courseInfo))
    

