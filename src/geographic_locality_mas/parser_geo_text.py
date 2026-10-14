"""Extract structured geographic context from DiSSCo specimen records."""
import re

#PARSER = regex.compile(r"(?<=\s|^)[A-Z](\p{Ll}+|\s+\p{Ll}{1,3}\s+)")
SEP =r'[,;.:]'

def parser_geo_text(p_term):
    global SEP
    results=[]
    tmp=[]
    #exploded=p_term.split(" ")
    exploded=re.split(SEP, p_term)
    #print(exploded)
    #exploded=[e for e in exploded if len(e)>0  ]  
    previous_lower=False
    previous_empty=False
    #print(exploded)
    for e in exploded:
        e=e.strip()
        exploded2=e.split(" ")
        i=0
        lowercase_list=[]
        for e2 in exploded2 :
            if e2.lower()!=e2 and len(e2)>1:
               lowercase_list.append("U")
            elif len(e2)>1 and len(e2)<=3:
               lowercase_list.append("J")
            else:
               lowercase_list.append("L")
        #print(exploded2)
        #print(lowercase_list)
        #i=0
        len_max=len(exploded2)
        acc=[]
        for i in range(0, len_max):
            if i==0: 
                if lowercase_list[i]=="U":
                    acc.append(exploded2[i])
            else:
                if lowercase_list[i]=="U":
                    acc.append(exploded2[i])
                elif lowercase_list[i]=="J" and i < len_max-1:
                    if lowercase_list[i-1]=="U" and lowercase_list[i+1]=="U":
                        acc.append(exploded2[i])
        #print(acc)
        if len(acc)>0:
            word=" ".join(acc)
            #print(word)
            results.append(word)
    return results


    
