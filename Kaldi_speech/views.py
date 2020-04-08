# 取消对于no-member的检查
# pylint: disable=no-member
from django.shortcuts import render
from django.http import HttpResponse
from Kaldi_speech.models import *
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from YouDaoAPI.text_translation import getTrans
from YouDaoAPI.text2speech import getSpeech
from django.core.exceptions import ObjectDoesNotExist
from Score.score import get_score
from django_redis import get_redis_connection
from Django_Kaldi.settings import *

import datetime
import re
import json
import os
import requests
import datetime
import hashlib
import logging

# 日志输出，不再使用print
logger = logging.getLogger(__name__)

# Create your views here.

'''
小程序维护登录状态
登录过程：
1. wx.login()获取res.code并用wx.request()发送res.code到第三方服务器(小程序后端);
2. 后端发送Get请求到微信服务器获取用户登录的open_id和session_key;
3. 后端收到open_id后判断数据库中是否存在
    不存在则创建用户对象;
4. 后端根据open_id和session_key生成一个3rd_session返回给小程序;
5. 后端将3rd_session存入Redis缓存中，设置时效2小时;
6. 小程序接收到3rd_session，则说明登录成功，并将3rd_session保存在本地,下次请求时,在请求头中携带3rd_session
7. 后台接收到请求，从请求头中拿到3rd_session，判断缓存中是否还有此3rd_session，
    如果有，说明还在登录态，允许执行请求相关操作，
    如果没有，说明需要重新登录，给小程序返回401.
ps: 如果后续需要对用户的open_id进行操作时，可以再向redis存储中添加一项，以3rd_session为键，open_id为key，这样可以保证服务器安全性
'''


def Index(request):
    try:
        # 尝试从redis中获取用户的open_id
        # 请求中header保存在META数据段中，且获取的办法为HTTP_XXX,XXX为变量名称
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION"))
        if open_id is None:
            changeSession = True
            # 如果获取不到，则返回None
            # 获取不到open_id,根据用户提供的code从微信故武器获取open_id
            code = request.META.get("HTTP_CODE")
            logger.debug('user code:{}'.format(code))
            data = {
                'appid': APP_ID,
                'secret': APP_SECRECT,
                'js_code': code,
                'grant_type': 'authorization_code'
            }
            res = json.loads(requests.get(WX_URL, params=data).content)
            logger.debug(res)
            if 'errcode' in res:
                # 获取出错时,直接返回
                logger.debug('获取用户信息失败，返回404')
                return HttpResponse(NOT_FOUND)
            else:
                # 登录成功
                open_id = res['openid']
                session_key = res['session_key']
                # 生成3rd_，返回给小程序
                sha = hashlib.sha1()
                sha.update(open_id.encode())
                sha.update(session_key.encode())
                session = sha.hexdigest()
                con = get_redis_connection('default')
                # 将 3rd_session 保存到缓存中, 十二个小时过期
                con.set(session, open_id, ex=12*60*60)
                # 测试缓存过期的情况，如果过期则需要用户重新登录
                # 返回open_id,并在小程序中存储在本地
        else:
            # 连接到default分区,获取不到时返回None,默认返回为Byte类型的数据，需要进行解码
            open_id = open_id.decode('utf-8')
            changeSession = False
            session = ""

        logger.debug("用户open_id "+open_id)
        # 计算用户学习天数
        td = datetime.datetime.now()
        curr_date = datetime.date(td.year, td.month, td.day)

        # get_or_create返回的是一个元组
        user_obj, isCreate = User.objects.get_or_create(open_id=open_id)
        logger.debug("新用户：",isCreate)
        if isCreate:
            # 当用户首次使用时也会更新学习记录
            logger.debug("新增学习记录")
            UserAttendance.objects.create(user=user_obj, attend_date=curr_date)
        # 只要用户点进小程序，即算学习一天
        # 获取当前时间，比对，不相同则learn-days加一天
        # 比较最后学习时间，如果不在同一天，则不修改
        # 如果用户首次进入

        if curr_date != user_obj.last_learn_time:
            logger.debug('更新用户学习天数')
            user_obj.learn_days += 1
            # 创建一个学习记录
            # 新增学习记录
            UserAttendance.objects.create(user=user_obj, attend_date=curr_date)
        user_obj.save()

        # 实际在首页还会显示用户学习天数等信息，点击开始学习直接进入上次未完成的课程，没有则直接进入课程列表
        # 获得每日格言
        motto = EveryDayMotto.objects.all()[0]

        motto_obj = {
            'motto': motto.motto,
            'author': motto.author,
            'poster': motto.poster.url,
            'learn_days': user_obj.learn_days,
            'curr_course': user_obj.curr_course,
            'status': 200,
            'changeSession': changeSession,
            'session': session
        }
        return HttpResponse(json.dumps(motto_obj))
    except:
        return HttpResponse(NOT_FOUND)


def getCourseInfo(request):
    order = request.GET['order']
    logger.debug('课程要求排列顺序为 ： {}'.format(order))
    if order == 'default':
        course_objs = Course.objects.all()
    elif order == 'heat':
        # 按照学习人数从大到小排序，需要反序
        course_objs = Course.objects.order_by('num_learners').reverse()
    elif order == 'new':
        # 按时间排序默认是按添加事件的先后，此处需要反序
        course_objs = Course.objects.order_by('add_time').reverse()
    else:
        # 出现其他请求时
        return HttpResponse(NOT_FOUND)

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

    # print(request.session['open_id'])
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

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
        uc_obj = UserCourse.objects.create(
            user=user_obj, course=course_obj, curr_section=curr_section)

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

    for sec in section_objs:
        # 获取用户完成状况
        try:
            us_obj = UserSection.objects.get(user=user_obj, section=sec)
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

    # 获取用户open_id，修改相关信息
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

    section_id = int(request.GET['section_id'])

    sen_obj = {}

    user_obj = User.objects.get(open_id=open_id)

    section_obj = Section.objects.get(id=section_id)

    course_obj = Course.objects.get(id=section_obj.course.id)

    objs = section_obj.sentence_set.all()

    # 更新当前章节
    uc_obj = UserCourse.objects.get(user=user_obj, course=course_obj)
    uc_obj.curr_section = section_obj.id
    uc_obj.save()

    # 例句数不为0
    if len(objs) != 0:
        curr_sentence = objs[0].id
        # 更新用户数据和用户课程数据库
        try:
            us_obj = UserSection.objects.get(
                user=user_obj, section=section_obj)
            curr_sentence = us_obj.curr_sentence
        except ObjectDoesNotExist:
            us_obj = UserSection.objects.create(
                user=user_obj, section=section_obj, curr_sentence=curr_sentence)

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
            for verb in re.findall(r'[~`!@#$%^&*()_\-+={}\[\]\|\\:;"\'<,.>?/]+|[A-Za-z\']+', obj.sentence_en):
                sep.append({
                    'verb': verb,
                    'isBad': False
                })

            logger.debug(sep)

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

        sen_obj['status'] = 200
    else:
        sen_obj['status'] = 500

    return HttpResponse(json.dumps(sen_obj))


def updataStudyStatus(request):
    # 获取用户当前学习状况
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

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
                UserSentence.objects.get(user=user_obj, sentence=sen)
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
        uc_obj = UserCourse.objects.get(user=user_obj, course=course_obj)
        sec_objs = course_obj.section_set.all()

        section_finish = []

        for sec in sec_objs:
            try:
                temp_obj = UserSection.objects.get(user=user_obj, section=sec)
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
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

    pattern = r'(\w{1,10}\.)\s(.*)'

    verb = request.GET['verb'].lower()

    user_obj = User.objects.get(open_id=open_id)

    logger.debug('looking for verb: {}'.format(verb))

    try:
        # 尝试从数据库中获取单词信息
        verbObj = Verb.objects.get(verb=verb)
        logger.debug('数据库中已经存在了嗷')
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
        UserVerb.objects.get(user=user_obj, verb=verbObj)
        isFav = True
        logger.debug('用户收藏过这个单词了嗷')
    except ObjectDoesNotExist:
        isFav = False
        logger.debug('用户没收藏过这个单词嗷')

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
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

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
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

    user_obj = User.objects.get(open_id=open_id)

    vb_objs = user_obj.userverb_set.all()

    res_obj = {}

    # 判断用户是否有收藏过单词
    if len(vb_objs) == 0:
        res_obj['hasVerb'] = False
    else:
        logger.debug('用户有收藏过单词嗷')

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
        try:
            open_id = get_redis_connection('default').get(
                request.META.get("HTTP_SESSION")).decode('utf-8')
        except AttributeError:
            return HttpResponse(SESSION_INVALID)

        judge_type = request.POST['type']
        logger.debug('Type: {}'.format(judge_type))
        # 采用read直接读取二进制文件，对于较大文件不便使用，但此处用户录音一般不超过一分钟，可以使用
        # 尝试直接保存用户发音
        # user_audio = ContentFile(request.FILES['audio'].read())
        user_audio = request.FILES['audio'].read()
        logger.debug('audio file size:{}'.format(len(user_audio)))
        user_obj = User.objects.get(open_id=open_id)

        score = 0
        user_audio_src = ''
        # 分为两种评分形式，对单词评分和对句子评分
        if judge_type == 'verb':
            # score = getScore()
            # try save audio file
            verb_id = int(request.POST['verb_id'])
            verb_obj = Verb.objects.get(id=verb_id)

            audio_file_path = os.path.join(MEDIA_ROOT, 'temp', 'temp_verb.mp3')
            # 这里收到的文件大小为0，有问题
            logger.debug('audio file size: {}'.format(len(user_audio)))
            with open(audio_file_path, 'wb') as audio_file:
                audio_file.write(user_audio)
            audio_file.close()

            res = get_score(GOP_ROOT, 'temp_verb',
                            audio_file_path, verb_obj.verb.upper())

            if res == -1:
                return HttpResponse(json.dumps({'error_code': 50}))
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
                os.system('rm {}'.format(temp_path))
                ua_obj.audio.save('{}_{}.mp3'.format(
                    user_obj.id, sentence_id), ContentFile(user_audio))
                logger.debug('用户以前发音过')
            except ObjectDoesNotExist:
                logger.debug('用户第一次发音')
                ua_obj = UserSentence.objects.create(
                    user=user_obj, sentence=sentence_obj, score=score)
                ua_obj.audio.save('{}_{}.mp3'.format(
                    user_obj.id, sentence_id), ContentFile(user_audio))

            user_audio_src = ua_obj.audio.url
            FileName = '{}_{}'.format(user_obj.id, sentence_id)
            # 需要提前对例句进行处理，去除所有标点符号
            # 建议在添加例句时就对例句进行处理
            # 添加一个数据像：sentence_en_upper
            # 但添加时就对数据进行处理
            if sentence_obj.sentence_upper == '@default':
                # 对例句进行处理，去除标点并转为大写
                logger.debug(sentence_obj.sentence_en)
                verb_list = re.findall(
                    r'[A-Za-z\']+', sentence_obj.sentence_en)
                sentence_upper = ' '.join(verb_list)
                sentence_obj.sentence_upper = sentence_upper.upper()
                sentence_obj.save()
            logger.debug(sentence_obj.sentence_upper)
            res = get_score(GOP_ROOT, FileName, ua_obj.audio.path,
                            sentence_obj.sentence_upper)
            # res = -1
            if res == -1:
                return HttpResponse(json.dumps({'error_code': 50}))
            ua_obj.score = res['score']
            ua_obj.save()
            res['user-audio'] = user_audio_src
            res['error_code'] = 0

        return HttpResponse(json.dumps(res))
    else:
        return HttpResponse(BAD_REQUEST_TYPE)


def getAudioList(request):
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

    user_obj = User.objects.get(open_id=open_id)

    va_objs = user_obj.usersentence_set.all()

    res_obj = {}

    # 判断用户是否有过录音
    if len(va_objs) == 0:
        res_obj['hasAudio'] = False
    else:
        logger.debug('用户有录音嗷')

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
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)

    order = request.GET['order']

    user_obj = User.objects.get(open_id=open_id)

    if order == '1':
        course_objs = UserCourse.objects.filter(user=user_obj)
    elif order == '2':
        # 已经完成的课程
        course_objs = UserCourse.objects.filter(user=user_obj, is_finish=False)
    elif order == '3':
        # 未完成的课程
        course_objs = UserCourse.objects.filter(user=user_obj, is_finish=True)

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
            'id': uc_obj.course.id,
            'name': uc_obj.course.name,
            'img': uc_obj.course.course_img.url,
            'curr': num_finish,
            'total': len(section_set),
        })

    return HttpResponse(json.dumps(courseInfo))


def getAccessToken():
    # 所有需要获取微信小程序接口访问权限都需要调用此函数来获取
    connection = get_redis_connection('default')
    access_token = connection.get('access_token')
    if access_token is None:
        data = {
            'appid': APP_ID,
            'secret': APP_SECRECT,
            'grant_type': 'client_credential'
        }
        res = json.loads(requests.get(ACCESS_TOKEN_URL, data).content)
        logger.debug(res)
        if 'errcode' in res:
            raise Exception("get access token failed")
        access_token = res['access_token']
        # 凭证有效期7200s，两小时
        connection.set('access_token', access_token, 7000)
    return access_token


def TestFunction(request):
    access_token = getAccessToken()
    # 获取到access_token之后推送消息
    user_objs = User.objects.all()[0]
    data = {
        'access_token': access_token,
        'touser': user_objs.open_id,
        'template_id': MESSAGE_TEMPLATE_ID,
        'page': 'pages/index/index',
        'data': {
            'thing1': {
                'value': '每日打卡提醒'
            },
            'thing5': {
                'value': '开启元气满满的一天'
            },
            'character_string3': {
                'value': '0/21'
            },
            'date14': {
                'value': '9:00'
            },
        }
    }
    return HttpResponse(requests.post(SEND_URL, data).content)

# django-crontab,执行定时任务，每天早晨9：00提醒用户打卡学习


def sendSubscribeMessage():
    # 由于这个函数是由外部函数执行，其库需要单独引入，否则会报错
    # 获取access_token并保存在redis缓存中，有效期是2小时
    print("打卡了弟弟")
    access_token = getAccessToken()
    for user in User.objects.all():
        print("send message to {}".format(user.open_id))
        data = {
            'access_token': access_token,
            'touser': user.open_id,
            'template_id': MESSAGE_TEMPLATE_ID,
            'page': 'pages/index/index',
            'data': {
                'thing1': {
                    'value': '每日打卡提醒'
                },
                'thing5': {
                    'value': '开启元气满满的一天'
                },
                'character_string3': {
                    'value': '0/21'
                },
                'date14': {
                    'value': '9:00'
                },
            }
        }
        print(requests.post(SEND_URL, data).content)


# 获取用户的某个时间段的打卡记录


def getUserCalendar(request):
    try:
        open_id = get_redis_connection('default').get(
            request.META.get("HTTP_SESSION")).decode('utf-8')
    except AttributeError:
        return HttpResponse(SESSION_INVALID)
    # 请求的数据是一个标准的时间字符串
    # 获取请求的时间段 对其进行处理 get 的参数分别为起始、结束
    # 将字符串处理为标准deteTime
    date_from = datetime.datetime.strptime(
        request.GET['date_from'], "%Y-%m-%d")
    date_to = datetime.datetime.strptime(
        request.GET['date_to'], "%Y-%m-%d")
    # 获取当前用户
    user_obj = User.objects.get(open_id=open_id)
    # 获取当前用户的目标范围内的打卡记录
    attend_objs = []

    for obj in UserAttendance.objects.filter(attend_date__range=(date_from, date_to), user=user_obj):
        attend_objs.append(obj.attend_date.isoformat())

    # 获取当前用户的最长打卡时间
    learndays = user_obj.learn_days
    # 获取低于当前用户打卡时间的用户数和总用户数并计算击败的比例
    less_count = User.objects.filter(learn_days__lt=learndays).count()
    user_count = User.objects.filter().count()
    ratio = float(less_count)/float(user_count)
    res_obj = {}

    # 传回数据分别为  区间内日期的数组  总学习天数  当前日期内参数 超越比例
    temp_obj = {
        'date': attend_objs,
        # 总学习天数
        'learndays': learndays,
        # 当月累计学习天数
        'attend_days': len(attend_objs),
        'ratio': ratio

    }

    return HttpResponse(json.dumps(temp_obj))
