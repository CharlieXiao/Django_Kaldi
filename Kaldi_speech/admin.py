from django.contrib import admin
from Kaldi_speech.models import EveryDayMotto,Course,Section,Sentence,Verb,VerbExplain,User,UserCourse,UserVerb,UserSentence,UserSection

# Register your models here.


# 指定后台网页要显示的字段，对于每日一句则显示作者和格言
class EveryDayMottoAdmin(admin.ModelAdmin):
    list_display = ["id","author","motto"]

class UserAdmin(admin.ModelAdmin):
    list_display = ["id","add_time","last_learn_time","learn_days"]

admin.site.register(EveryDayMotto,EveryDayMottoAdmin)

admin.site.register(Course)

admin.site.register(Section)

admin.site.register(Sentence)
    
admin.site.register(Verb)

admin.site.register(VerbExplain)

admin.site.register(User,UserAdmin)

admin.site.register(UserCourse)

admin.site.register(UserVerb)

admin.site.register(UserSentence)

admin.site.register(UserSection)
