from django.db import models
from django.utils import timezone

# Create your models here.

# 每日格言
class EveryDayMotto(models.Model):
    motto = models.CharField(max_length=100,verbose_name="Motto",default="Life is like a boat")
    author = models.CharField(max_length=50,verbose_name="Author",default="Rie fu")
    poster = models.ImageField(upload_to='motto/poster',verbose_name="poster",default='default/default.png')
    audio = models.FileField(upload_to='motto/audio',verbose_name="audio")

    def __str__(self):
        return self.author + " " + self.motto

def course_directory_path(instance,filename):
    # 文件路径会上传到 MEDIA_ROOT/course/course_<id>/section_<id>/filename
    return 'course/img/{0}'.format(filename)        

# 课程数据库
class Course(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100,verbose_name="name")
    intro = models.CharField(max_length=200,verbose_name="introduction")
    num_sections = models.IntegerField(verbose_name="sections",default=0)
    course_img = models.ImageField(upload_to=course_directory_path,verbose_name="poster",default='default/default.png')
    num_learners = models.IntegerField(verbose_name="learners",default=0)
    add_time = models.DateTimeField(verbose_name="add time",auto_now_add=True)

    def __str__(self):
        return self.name

class Section(models.Model):
    # 章节对应的课程
    course = models.ForeignKey("Course",on_delete=models.CASCADE)
    title = models.CharField(max_length=100,verbose_name="title")
    subtitle = models.CharField(max_length=200,verbose_name="subtitle")
    num_sentences = models.IntegerField(verbose_name="sentences",default=0)
    
    def __str__(self):
        return self.course.name+" "+self.title

def section_directory_path(instance,filename):
    # 文件路径会上传到 MEDIA_ROOT/course/course_<id>/section_<id>/filename
    return 'course/course_{0}/section_{1}/{2}'.format(instance.section.course.id,instance.section.id,filename)

class Sentence(models.Model):
    section = models.ForeignKey("Section",on_delete=models.CASCADE)
    sentence_en = models.CharField(max_length=200,verbose_name="English")
    sentence_ch = models.CharField(max_length=200,verbose_name="Chinese")
    sentence_src = models.FileField(upload_to=section_directory_path,verbose_name="audio",default='default/default.wav')

    # 期望直接在创建models对象时直接连接有道云查询相关句子发音

    def __str__(self):
        return self.section.title+" "+self.sentence_en

class Verb(models.Model):
    verb = models.CharField(max_length=50,verbose_name="vocabulary")
    uk_phonetic = models.CharField(max_length=100,verbose_name='uk phonetic')
    us_phonetic = models.CharField(max_length=100,verbose_name='us phonetic')
    uk_speech = models.FileField(upload_to='verb/',verbose_name='uk speech',default='default/default.wav')
    us_speech = models.FileField(upload_to='verb/',verbose_name='us speech',default='default/default.wav')

    def __str__(self):
        return self.verb

class VerbExplain(models.Model):
    # Django会默认以模型的！！！全部小写！！！加上_set作为反向关联名
    # 即 可以通过Verb.VerbExplain_set来访问其单词解释
    verb = models.ForeignKey("Verb",on_delete=models.CASCADE)
    pos = models.CharField(max_length=20,verbose_name='part of speech')
    explain = models.CharField(max_length=200,verbose_name='explain')

    def __str__(self):
        return self.verb.verb + " " + self.pos + " " + self.explain

class User(models.Model):
    open_id = models.CharField(max_length=100,verbose_name='user open id')
    # 保存用户加入时间
    learn_days = models.DateField(verbose_name='add time',auto_now_add=True)

    def __str__(self):
        return self.open_id

class UserVerb(models.Model):
    # 中间表，连接用户数据库和单词数据库
    user = models.ForeignKey("User",on_delete=models.CASCADE)
    verb = models.ForeignKey('Verb',on_delete=models.CASCADE)

    def __str__(self):
        return self.user.open_id + ' ' + self.verb.verb

def useraudio_directory_path(instance,filename):
    return 'user/{}/{}'.format(instance.user.open_id,filename)

class UserCourse(models.Model):
    # 中间表，连接用户数据可和课程数据库
    user = models.ForeignKey("User",on_delete=models.CASCADE)
    # 只要知道当前例句即可对应到当且章节和当前课程
    curr_sentence = models.IntegerField(default=0,verbose_name='current sentence')
    # 用户录音
    audio = models.FileField(default='default/default.wav',upload_to=useraudio_directory_path,verbose_name='user audio')
    # 用户发音得分
    score = models.IntegerField(default=90,verbose_name='score')

    def __str__(self):
        curr_section = Section.objects.get(id=self.curr_sentence.section)
        curr_course = Course.objects.get(id=self.curr_section.course)
        return '{} : {} -> {} -> {}'.format(self.user.open_id,curr_course.name,curr_section.title,self.curr_sentence.sentence_en)
