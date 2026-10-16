import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1920
BLUE=(91,206,250); PINK=(245,169,184); WHITE=(255,255,255)
def flag():
    im=Image.new("RGB",(W,H)); d=ImageDraw.Draw(im)
    cols=[BLUE,PINK,WHITE,PINK,BLUE]; h=H/5
    for i,c in enumerate(cols): d.rectangle([0,int(i*h),W,int((i+1)*h)],fill=c)
    return im
SER="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
def card(lines, out, big=False):
    im=flag().convert("RGBA")
    ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
    f=ImageFont.truetype(SER, 150 if big else 58)
    hl=[d.textbbox((0,0),l,font=f) for l in lines]
    lh=(f.size*1.35); tot=lh*len(lines); y=(H-tot)/2
    d.rounded_rectangle([60,y-60,W-60,y+tot+40],radius=40,fill=(255,255,255,170))
    for l,b in zip(lines,hl):
        w=b[2]-b[0]; d.text(((W-w)/2,y),l,font=f,fill=(60,40,90),stroke_width=2 if big else 0,stroke_fill=(245,169,184))
        y+=lh
    Image.alpha_composite(im,ov).convert("RGB").save(out)
cards=[
 (["Nij"],True),
 (["Leram teu nome","da esquerda pra direita","e acharam que sabiam","quem você era."],False),
 (["Mas a verdade se lê","do jeito que o","coração espera."],False),
 (["JIN  →  NIJ"],False),
 (["Jin: ouro.","Você virou o espelho","e o ouro respondeu:"],False),
 (["Nij","= nova"],True),
 (["Nova não porque","nasceu de novo,","mas porque enfim nasceu","o que era seu."],False),
 (["O azul do céu de quem","aprendeu a voar sozinha."],False),
 (["O rosa da coragem","que floresce","sem pedir licença."],False),
 (["E no meio, o branco:","a página onde você","escreve a própria sentença."],False),
 (["Ninja"],True),
 (["Ninguém viu o treino,","só a chegada."],False),
 (["Contra o medo,","contra a dúvida,","contra o nada."],False),
 (["Você não se escondeu:","se lapidou.","Não fugiu: atravessou."],False),
 (["Quando o mundo tenta","te ler errado,","você sorri."],False),
 (["Nij. Nova. Inteira.","Ouro de trás pra frente.","Mulher do jeito","que sempre foi."],False),
]
import os
od=sys.argv[1]
for i,(l,b) in enumerate(cards): card(l,os.path.join(od,f"c{i:02d}.png"),b)
print(len(cards))
