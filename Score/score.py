import sys
import re
import os
import json
import time

def is_match(A, B):
    # A,B is two list, check if B is in A
    len_A = len(A)
    len_B = len(B)
    for i in range(len_A-len_B):
        a = A[i:i+len_B]
        # matched
        if a == B:
            return True
    # after all iteration
    # not found
    # return False
    return False

def normalize_phone(phone):
    pattern = re.compile(r'([A-Z]+)\d?_?[A-Z]')
    return pattern.match(phone).group(1)


def get_score(GopPath, FileName, FileSrc, Text, langModel='lang3', acousticModel='tri3'):
    '''
    Text must be upper case like 'HELLO WORLD'
    TextSep is ['WHAT','MAKES','THE','DESSERT','BEAUTIFUL']
    '''
    # FileName = '3_18'
    # FileSrc = '~/Django_Kaldi/media/user/3/3_18.mp3'
    RawWorkDir = os.getcwd()
    print('Curr Work Dir: {}'.format(os.getcwd()))
    os.chdir(GopPath)
    print('Curr Work Dir: {}'.format(os.getcwd()))
    AudioFilePath = os.path.join('audio', FileName)
    WavPath = os.path.join('audio', '{}.wav'.format(FileName))
    print('WAV Path: {}'.format(WavPath))

    # ffmpeg convert mp3 to wav by default
    print('Conver MP3 to WAV')
    res = os.system(
        'ffmpeg -y -i {} -ac 2 -ar 16000 {}'.format(FileSrc, WavPath))
    if res != 0:
        print("File convert failed.\nExit.")
        return -1

    # prepare data
    TargetPath = os.path.join('data', FileName)
    print('Target Path: {}'.format(TargetPath))
    # clear target path
    if os.path.exists(TargetPath):
        os.system('rm -rf {}'.format(TargetPath))
    os.mkdir(TargetPath)

    DataPrepDir = os.path.join(TargetPath, 'data_prep')

    os.mkdir(DataPrepDir)
    # generate 4 files
    spk2utt = open(os.path.join(DataPrepDir, 'spk2utt'), 'w+')
    utt2spk = open(os.path.join(DataPrepDir, 'utt2spk'), 'w+')
    file_text = open(os.path.join(DataPrepDir, 'text'), 'w+')
    wav_scp = open(os.path.join(DataPrepDir, 'wav.scp'), 'w+')

    # write files
    utt2spk.write('{} {}'.format(FileName, FileName))
    spk2utt.write('{} {}'.format(FileName, FileName))
    wav_scp.write('{} {}'.format(FileName, WavPath))
    file_text.write('{} {}'.format(FileName, Text.upper()))

    # close
    spk2utt.close()
    utt2spk.close()
    wav_scp.close()
    file_text.close()

    # Run
    print('Run Shell Script')
    # choose langModel and acoustic Model
    res = os.system('./run_django.sh {} {} {}'.format(FileName,
                                                      langModel, acousticModel))
    if res != 0:
        print('Run Shell Script Failed.')
        return -1

    ####################################################################################
    try:
        ResultDir = os.path.join(TargetPath, 'result')

        THRESHOLD_LEVEL_1 = -2.13557

        THRESHOLD_LEVEL_2 = -8.82741

        TextSep = Text.split(' ')

        # make phone_dict static
        # map the phone_id to the phone
        if not hasattr(get_score, 'phone_dic'):
            phone_dic = {}
            for line in open(os.path.join(ResultDir, 'phones.txt'), 'r'):
                temp = line.strip('\n').split(' ')
                p = temp[0]
                num = temp[1]
                phone_dic[num] = p

        # map the verb to the phone
        if not hasattr(get_score, 'verb_dic'):
            verb_dic = {}
            for line in open(os.path.join(GopPath, 'data', langModel, 'phones', 'align_lexicon.txt'), 'r'):
                temp = line.strip('\n').split(' ')
                if verb_dic.get(temp[0], None) is None:
                    verb_dic[temp[0]] = [temp[2:]]
                else:
                    verb_dic[temp[0]].append(temp[2:])

        if not hasattr(get_score, 'ignore_phones'):
            ignore_phones = [
                '<eps>', 'SIL', 'SIL_B', 'SIL_E', 'SIL_I', 'SIL_S', 'SPN', 'SPN_B', 'SPN_E', 'SPN_I', 'SPN_S', '#0', '#1', '#2', '#3', '#4', '#5', '#6', '#7', '#8', '#9', '#10', '#11', '#12', '#13', '#14', '#15', '#16', ]

        # Analyse Rsult

        # each phone in the phone_list is a dict like {'phone':'Y_I','verb':BEAUTIFUL,'level':3}

        # read file
        # acutualy the file has only one line
        score_list = []
        with open(os.path.join(ResultDir, 'gop.1')) as score_file:
            res = score_file.readline()
            score_list = res.split(' ')[3:-1]
            score_file.close()
        # print(score_list)

        phone_list = []
        with open(os.path.join(ResultDir, 'gop.2')) as phone_file:
            res = phone_file.readline()
            phone_index_list = res.split(' ')[1:-1]
            for index in phone_index_list:
                phone_list.append(phone_dic[index])
            phone_file.close()
        # print(phone_list)

        # generate verb map phone
        sentence = []
        verb_boundry = []
        for verb in TextSep:
            res = verb_dic[verb]
            # just one pronounciation
            # check if the pornounciation is in the phone_list
            has_match = False
            for verb_phones in res:
                if is_match(phone_list, verb_phones):
                    sentence.append({
                        'verb': verb.lower(),
                        'phones': verb_phones,
                        'isBad':False,
                        'BadPhoneList':[],
                    })
                    verb_boundry.append(len(verb_phones)-1)
                    has_match = True
                    break
            # after all the iteration, still not found, error
            if not has_match:
                return -1

        # #导入phones_threshold json文件
        # with open("phones_threshold.json",'r', encoding='UTF-8') as f:
        #     phones_threshold_dict = json.load(f)
        
        #print(phones_threshold_dict)

        CntLevel1 = 0
        CntLevel2 = 0
        CntLevel3 = 0

        verb_index = 0
        phone_index = 0

        for j in range(len(score_list)):
            # THRESHOLD_LEVEL_1 = phones_threshold_dict[phone_list[j]][1]
            # THRESHOLD_LEVEL_2 = phones_threshold_dict[phone_list[j]][0]
            
            if phone_list[j] in ignore_phones:
                continue
            # print("curr phone: {}\t\tcurr verb: {}\t\tcurr phone: {}".format(phone_list[j], sentence[verb_index]['verb'],sentence[verb_index]['phones'][phone_index]))
            if(float(score_list[j]) >= THRESHOLD_LEVEL_1):  # -1.13557
                CntLevel1 += 1
                sentence[verb_index]["phones"][phone_index] = {
                    'phone':normalize_phone(phone_list[j]),
                    'level':1
                }

            elif(float(score_list[j]) <= THRESHOLD_LEVEL_2):  # -3.82741
                CntLevel3 += 1
                sentence[verb_index]["phones"][phone_index] = {
                    'phone':normalize_phone(phone_list[j]),
                    'level':3
                }
                sentence[verb_index]["isBad"] = True
                sentence[verb_index]["BadPhoneList"].append(phone_index)
            else:
                CntLevel2 += 1
                sentence[verb_index]["phones"][phone_index] = {
                    'phone':normalize_phone(phone_list[j]),
                    'level':2
                }
            
            if phone_index < verb_boundry[verb_index]:
                phone_index += 1
            else:
                phone_index = 0
                verb_index += 1

        denominator = 5*(CntLevel1+CntLevel2+CntLevel3)
        numerator = CntLevel1*5 + CntLevel2*3 + CntLevel3*1
        sentence_info = {
            'score': int(numerator / denominator * 100),
            'sentence': sentence
        }
        os.chdir(RawWorkDir)
        return sentence_info
    except:
        return -1

    


if __name__ == "__main__":
    start_time = time.time()
    print(get_score('/home/ljh/kaldi-test/kaldi-trunk/egs/gop-compute_server', 'good',
                    '/home/ljh/audio/good.mp3', 'WHAT MAKES THE DESSERT BEAUTIFUL'))
    end_time = time.time()
    print("Start_time: {}".format(start_time))
    print("End_time: {}".format(end_time))
    print("Total Use: {}".format(end_time-start_time))

# if __name__ == "__main__":
#     start_time = time.time()
#     print(get_score('/home/ubuntu/kaldi/egs/gop-compute', '11',
#                     '/home/ubuntu/Django_Kaldi/media/course/course_6/section_4/11.mp3', 'WHAT MAKES THE DESSERT BEAUTIFUL'))
#     end_time = time.time()
#     print("Start_time: {}".format(start_time))
#     print("End_time: {}".format(end_time))
#     print("Total Use: {}".format(end_time-start_time))