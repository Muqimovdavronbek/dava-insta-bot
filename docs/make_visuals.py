"""Rebuild README artwork. The chat illustration is a labelled demo, not a live screenshot."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
BOLD=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
def font(size,bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT),size)
def text(draw,xy,value,size=24,fill='#E9F3FF',bold=False):
    draw.text(xy,value,font=font(size,bold),fill=fill)
def rounded(draw,box,fill,radius=22,outline=None):
    draw.rounded_rectangle(box,radius,fill=fill,outline=outline,width=2)

im=Image.new('RGB',(1440,760),'#071322'); d=ImageDraw.Draw(im)
for x in range(0,1440,48): d.line((x,0,x,760),fill='#0C1C2E')
for y in range(0,760,48): d.line((0,y,1440,y),fill='#0C1C2E')
rounded(d,(64,58,305,100),'#103E47',18)
text(d,(82,68),'PYTHON  /  TELEGRAM',18,'#70E5DB',True)
text(d,(64,129),'Dava Insta Bot',76,bold=True)
text(d,(68,231),'Instagram linklari. Bitta TXT. Tartibli yuklash.',29,'#A3B9CD')
steps=[('01','TXT yuboring','Linklar bitta ro‘yxatda'),('02','Bot yuklaydi','Keyingi post oldindan tayyor'),('03','Fayllarni oling','#1   #2   #3   ...')]
for i,(number,title,body) in enumerate(steps):
    x=64+i*448
    rounded(d,(x,335,x+416,544),'#102237',22,'#24425D')
    text(d,(x+26,358),number,33,'#52D9CB',True)
    text(d,(x+26,414),title,29,bold=True)
    text(d,(x+26,467),body,20,'#A3B9CD')
    if i<2:
        d.line((x+423,437,x+439,437),fill='#52D9CB',width=3)
        d.polygon([(x+439,437),(x+432,431),(x+432,443)],fill='#52D9CB')
labels=['Tartib saqlanadi','Har fayl raqamlanadi','Navbat tiklanadi']
for i,label in enumerate(labels):
    x=64+i*448
    d.ellipse((x,602,x+12,614),fill='#52D9CB')
    text(d,(x+24,590),label,22,'#BBD0E3')
text(d,(66,693),'Ochiq kod  •  O‘zbekcha yo‘riqnoma  •  Linux',20,'#738EA6')
im.save(ROOT/'assets/banner.png',optimize=True)

im=Image.new('RGB',(1000,1080),'#081522');d=ImageDraw.Draw(im)
text(d,(48,34),'FAYLLAR QANDAY KELADI?',25,'#65DFD2',True)
text(d,(48,79),'Telegram ko‘rinishining namuna rasmi',23,'#9FB3C7')
rounded(d,(48,139,952,1024),'#12263A',28,'#28415A')
d.ellipse((75,163,139,227),fill='#1E7E8C')
text(d,(89,179),'DI',23,bold=True)
text(d,(158,167),'Dava Insta Bot',28,bold=True)
text(d,(159,204),'shaxsiy bot',19,'#80B3CE')
d.line((74,248,926,248),fill='#2A4259',width=2)
rounded(d,(425,274,921,353),'#205365',15)
text(d,(449,289),'instagram_links.txt',24,bold=True)
text(d,(450,322),'3 ta Instagram post',16,'#B8D6DF')
for i in range(3):
    y=387+i*177
    rounded(d,(78,y,786,y+151),'#1D354C',17)
    rounded(d,(99,y+21,162,y+88),'#225A68',12)
    text(d,(110,y+42),'MP4',16,'#88EFDF',True)
    text(d,(184,y+23),f'00{i+1}_video.mp4',24,bold=True)
    text(d,(184,y+61),'Video fayl',18,'#9DB8CE')
    text(d,(102,y+103),f'#{i+1}   •   Ro‘yxatdagi keyingi fayl',21,'#6BE5D5',True)
text(d,(81,959),'NAMUNA • Haqiqiy hisob yoki video ma’lumoti ishlatilmagan',16,'#8BA3B9')
im.save(ROOT/'assets/numbering-demo.png',optimize=True)
print('README images generated.')
