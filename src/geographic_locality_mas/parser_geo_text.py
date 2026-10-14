"""Extract structured geographic context from DiSSCo specimen records."""
import re

#PARSER = regex.compile(r"(?<=\s|^)[A-Z](\p{Ll}+|\s+\p{Ll}{1,3}\s+)")
SEP =r'[\s,;.:]'




def parser_geo_text(p_term):
    global SEP
    results=[]
    tmp=[]
    #exploded=p_term.split(" ")
    exploded=re.split(SEP, p_term)
    exploded=[e for e in exploded if len(e)>0  ]  
    previous_lower=False
    for e in exploded:        
        if e[0]==e[0].upper() and len(e)>=2 and not e[0].isdigit(): 
            if len(tmp)>0 and previous_lower==False:
                word=" ".join(tmp)
                results.append(word)
                #previous_lower=False
                tmp=[]
            tmp.append(e)  
            previous_lower=False            
        elif len(e)<=3 and len(tmp)>0 and e.lower()==e and not previous_lower and not e[0].isdigit():
            tmp.append(e)   
            previous_lower=True
        else:
            word=" ".join(tmp)
            if len(word)>0:
                results.append(word)
                previous_lower=False
            tmp=[]
    if len(tmp)>0:
        word=" ".join(tmp)
        if len(word)>0:
            results.append(word)
            previous_lower=False
    results_tmp=[]
    for r in results:
        test=r.split(" ")
        if len(test)==2:
            if test[1]==test[1].lower():
                r=test[0]
        results_tmp.append(r)
    results= results_tmp   
    return results
    
