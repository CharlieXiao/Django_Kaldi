from django.db import models
from django.utils import timezone

# Create your models here.

# 每日格言


class EveryDayMotto(models.Model):
    motto = models.CharField(
        max_length=100, verbose_name="格言", default="Life is like a boat")
    author = models.CharField(
        max_length=50, verbose_name="作者", default="Rie fu")
    poster = models.ImageField(
        upload_to='motto/poster', verbose_name="封面", default='default/default.png')
    audio = models.FileField(upload_to='motto/audio',
                             verbose_name="音频", default='default/default.wav')

    def __str__(self):
        return self.author + " " + self.motto


def course_directory_path(instance, filename):
    # 文件路径会上传到 MEDIA_ROOT/course/course_<id>/section_<id>/filename
    return 'course/img/{0}'.format(filename)

# 课程数据库


class Course(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="课程名称")
    intro = models.CharField(
        max_length=200, verbose_name="课程介绍", default='写点介绍吧...')
    # num_sections = models.IntegerField(verbose_name="课程章节", default=0)
    course_img = models.ImageField(
        upload_to=course_directory_path, verbose_name="课程封面", default='default/default.png')
    num_learners = models.IntegerField(verbose_name="学习人数", default=0)
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    def __str__(self):
        return self.name


class Section(models.Model):
    # 章节对应的课程
    course = models.ForeignKey("Course", on_delete=models.CASCADE)
    title = models.CharField(max_length=100, verbose_name="章节标题")
    subtitle = models.CharField(max_length=200, verbose_name="章节副标题")
    # num_sentences = models.IntegerField(verbose_name="章节例句数", default=0)

    def __str__(self):
        return '{} - {}'.format(self.course.name, self.title)


def section_directory_path(instance, filename):
    # 文件路径会上传到 MEDIA_ROOT/course/course_<id>/section_<id>/filename
    return 'course/course_{0}/section_{1}/{2}'.format(instance.section.course.id, instance.section.id, filename)


class Sentence(models.Model):
    section = models.ForeignKey("Section", on_delete=models.CASCADE)
    sentence_en = models.CharField(max_length=200, verbose_name="英文例句")
    sentence_ch = models.CharField(max_length=200, verbose_name="中文释义")
    sentence_upper = models.CharField(max_length=200,verbose_name="不带标点大写[无需填写]",default="@default")
    sentence_src = models.FileField(
        upload_to=section_directory_path, verbose_name="例句音频", default='default/default.wav')

    # 期望直接在创建models对象时直接连接有道云查询相关句子发音

    def __str__(self):
        return self.section.title+"->"+self.sentence_en


class Verb(models.Model):
    verb = models.CharField(max_length=50, verbose_name="词汇")
    uk_phonetic = models.CharField(max_length=100, verbose_name='英式英标')
    us_phonetic = models.CharField(max_length=100, verbose_name='美式英标')
    uk_speech = models.FileField(
        upload_to='verb/', verbose_name='英式发音', default='default/default.wav')
    us_speech = models.FileField(
        upload_to='verb/', verbose_name='美式发音', default='default/default.wav')

    def __str__(self):
        return self.verb


class VerbExplain(models.Model):
    # Django会默认以模型的！！！全部小写！！！加上_set作为反向关联名
    # 即 可以通过Verb.VerbExplain_set来访问其单词解释
    verb = models.ForeignKey("Verb", on_delete=models.CASCADE)
    pos = models.CharField(max_length=20, verbose_name='词性')
    explain = models.CharField(max_length=200, verbose_name='释义')

    def __str__(self):
        return self.verb.verb + " " + self.pos + " " + self.explain


class User(models.Model):
    open_id = models.CharField(max_length=100, verbose_name='用户ID')

    # 保存用户加入时间
    add_time = models.DateField(verbose_name='添加事件', auto_now_add=True)

    # 最后一次学习时间，自动保存为更新时间
    # 设置为true时，每次执行 save 操作时，将其值设置为当前时间
    last_learn_time = models.DateField(verbose_name='最后学习时间', auto_now=True)

    # 累计学习天数，默认为第一天
    learn_days = models.IntegerField(verbose_name='学习天数', default=1)

    # 由于一个用户可以学习多个课程，但只有一个是用户当前正在学习的，因此需要记录

    # 当前课程，仅记录id
    curr_course = models.IntegerField(
        verbose_name='当前学习课程', default=-1)

    def __str__(self):
        return self.open_id


def useraudio_directory_path(instance, filename):

    return 'user/{}/{}'.format(instance.user.id, filename)


class UserVerb(models.Model):
    # 中间表，连接用户数据库和单词数据库
    user = models.ForeignKey("User", on_delete=models.CASCADE)

    verb = models.ForeignKey('Verb', on_delete=models.CASCADE)

    def __str__(self):
        return '{} : {}'.format(self.user.id, self.verb.verb)

# 设置默认值


def course_default():
    objs = Course.objects.all()
    if len(objs) == 0:
        # 不存在课程，添加一个，但最好直接存在，按理课程一定存在
        print('不存在课程，请及时添加课程')
    else:
        # 返回第一个课程
        return objs[0].id

# 添加bool标签判断用户是否学习完课程

class UserCourse(models.Model):
    # 中间表，连接用户数据可和课程数据库
    # 存储用户学习所有课程
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    # 只要知道当前例句即可对应到当且章节和当前课程

    course = models.ForeignKey("Course", on_delete=models.CASCADE)

    # 只要存储对应课程学习章节的id即可
    curr_section = models.IntegerField(default=-1, verbose_name='当前章节')

    is_finish = models.BooleanField(default=False,verbose_name='是否完成')

    def __str__(self):
        return '{} : {} -> {} | {}'.format(self.user.id, self.course.name, self.curr_section,self.is_finish)

# 添加一个bool标签来判断用户是否已经学习完成这个章节

class UserSection(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)

    section = models.ForeignKey("Section", on_delete=models.CASCADE)

    curr_sentence = models.IntegerField(default=-1, verbose_name='当前例句')

    is_finish = models.BooleanField(default=False,verbose_name='是否完成')

    def __str__(self):
        return '{} : {} -> {} | {}'.format(self.user.id, self.section.title, self.curr_sentence,self.is_finish)


class UserSentence(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)

    sentence = models.ForeignKey("Sentence", on_delete=models.CASCADE)

    score = models.IntegerField(default=90, verbose_name="得分")

    audio = models.FileField(default='default/default.wav',
                             upload_to=useraudio_directory_path, verbose_name='用户音频')

    def __str__(self):
        return '{} : {} {}'.format(self.user.id, self.sentence.id, self.score)
