"""Seed idempotente: python -m scripts.seed_problemas_tipicos"""
import re, unicodedata
from database import SessionLocal
import main  # registra todos os models antes de configurar os relacionamentos
from models.familias_models import TipoAtivo
from models.problemas_tipicos_models import ProblemaTipico, SintomaProblema, CausaProblema, AcaoRecomendada, MetodoDeteccaoProblema

def norm(s): return re.sub(r"[^A-Z0-9]","",unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().upper())
CATALOGO={
 "TRANSFORMADOR REATOR":[("Aquecimento anormal","ALTA"),("Vazamento de óleo","MEDIA"),("Gases anormais no óleo","CRITICA")],
 "DISJUNTOR":[("Falha de abertura","CRITICA"),("Falha de fechamento","ALTA"),("Tempo de operação elevado","ALTA"),("Baixa pressão/densidade de SF6","ALTA"),("Discordância de polos","CRITICA"),("Aquecimento em conexões","ALTA")],
 "SECCIONADORA":[("Falha de abertura","ALTA"),("Falha de fechamento","ALTA"),("Mau contato","ALTA"),("Aquecimento","ALTA"),("Desalinhamento","MEDIA"),("Falha no motor de acionamento","MEDIA"),("Problema de fim de curso","MEDIA"),("Corrosão do mecanismo","MEDIA")],
 "TC":[("Aquecimento anormal","ALTA"),("Relação incorreta","ALTA"),("Secundário aberto","CRITICA"),("Vazamento","MEDIA"),("Deterioração do isolamento","ALTA"),("Problema em caixa secundária","ALTA"),("Oxidação de conexões","MEDIA")],
 "TP TPC":[("Tensão secundária incorreta","ALTA"),("Falha de fusível","ALTA"),("Vazamento de óleo","MEDIA"),("Aquecimento","ALTA"),("Problema de isolamento","ALTA"),("Falha no circuito secundário","ALTA")],
 "PARA RAIOS":[("Corrente de fuga elevada","ALTA"),("Aquecimento anormal","ALTA"),("Contador de descargas defeituoso","MEDIA"),("Trinca/dano físico","ALTA"),("Problema no aterramento","ALTA")],
 "BANCO DE BATERIAS":[("Baixa tensão de elemento","ALTA"),("Resistência interna elevada","ALTA"),("Oxidação dos terminais","MEDIA"),("Vazamento","MEDIA"),("Elemento deteriorado","ALTA"),("Falha de conexão","ALTA")],
 "RETIFICADOR":[("Falha de carregamento","ALTA"),("Tensão CC elevada","ALTA"),("Tensão CC baixa","ALTA"),("Falha de alimentação CA","ALTA"),("Falha de módulo","ALTA"),("Alarme de temperatura","MEDIA"),("Falha de comunicação","MEDIA")],
 "PROTECAO CONTROLE":[("Falha de alimentação CC","CRITICA"),("Relé indisponível","CRITICA"),("Falha de comunicação","ALTA"),("Autodiagnóstico do IED","ALTA"),("Divergência de estado","ALTA"),("Falha de comando","ALTA"),("Falha de circuito de trip","CRITICA"),("Falha de circuito de fechamento","ALTA"),("Oscilografia indisponível","MEDIA"),("Sincronismo indisponível","ALTA")],
 "TELECOMUNICACOES":[("Perda de comunicação","ALTA"),("Atenuação elevada em fibra","ALTA"),("Falha de switch","ALTA"),("Porta óptica defeituosa","ALTA"),("Falha de alimentação","ALTA"),("Intermitência de comunicação","MEDIA"),("Perda de canal de teleproteção","CRITICA")],
 "CONDUTOR":[("Tentos rompidos","ALTA"),("Emenda aquecendo","CRITICA"),("Flecha excessiva","ALTA"),("Danos por descarga","ALTA"),("Oxidação/corrosão","MEDIA"),("Vibração excessiva","MEDIA")],
 "ISOLADOR":[("Isolador quebrado","CRITICA"),("Trinca em isolador","ALTA"),("Contaminação","MEDIA"),("Descarga superficial","ALTA"),("Marcas de arco","ALTA"),("Ferragem danificada","ALTA")],
 "TORRE":[("Corrosão da torre","ALTA"),("Parafuso ausente","ALTA"),("Parafuso frouxo","ALTA"),("Perfil deformado","CRITICA"),("Dano estrutural","CRITICA"),("Vandalismo","ALTA")],
 "FUNDACAO":[("Trinca na fundação","ALTA"),("Erosão na fundação","ALTA"),("Recalque","CRITICA"),("Exposição da fundação","ALTA"),("Problema de drenagem","MEDIA")],
 "ATERRAMENTO":[("Resistência elevada","ALTA"),("Contrapeso rompido","ALTA"),("Corrosão do aterramento","MEDIA"),("Conexão deficiente","ALTA"),("Furto de condutor","CRITICA")],
 "OPGW":[("Fios rompidos","ALTA"),("Atenuação óptica elevada","ALTA"),("Rompimento de fibra","CRITICA"),("Problema em caixa de emenda","ALTA"),("Dano por descarga atmosférica","ALTA")],
 "FAIXA SERVIDAO":[("Vegetação alta","ALTA"),("Árvore em risco","CRITICA"),("Construção irregular","ALTA"),("Queimada","CRITICA"),("Erosão na faixa de servidão","ALTA"),("Acesso bloqueado","MEDIA")],
 "ACESSORIOS":[("Espaçador danificado","ALTA"),("Amortecedor Stockbridge danificado","MEDIA"),("Jumper aquecendo","CRITICA"),("Jumper com distância inadequada","ALTA"),("Esfera de sinalização ausente","MEDIA"),("Placa de identificação ausente","BAIXA")],
}
def candidatos(chave, tipos):
 nomes={
  "TRANSFORMADOR REATOR":["REATOR DERIVACAO","REATOR DE NEUTRO","TRANSFORMADOR DE POTENCIA","TRANSFORMADOR"],
  "TC":["TRANSFORMADOR DE CORRENTE"], "TP TPC":["TRANSFORMADOR DE POTENCIAL","TRANSFORMADOR DE POTENCIAL CAPACITIVO","TPC","TP"],
  "PROTECAO CONTROLE":["RELE DE PROTECAO","PAINEL","SINCRONIZADOR","SUPERVISORIO","REGISTRADOR DE PERTURBACOES"],
  "PARA RAIOS":["PARA RAIOS"],
  "CONDUTOR":["TORRE"], "ISOLADOR":["TORRE"], "TORRE":["TORRE"], "FUNDACAO":["TORRE"],
  "ATERRAMENTO":["TORRE"], "OPGW":["TORRE"], "FAIXA SERVIDAO":["TORRE"], "ACESSORIOS":["TORRE"],
 }
 alvos=[norm(x) for x in nomes.get(chave,[chave])]
 return [t for t in tipos if norm(t.nome) in alvos]
def main():
 db=SessionLocal(); tipos=db.query(TipoAtivo).all(); criados=0
 try:
  for grupo, problemas in CATALOGO.items():
   for tipo in candidatos(grupo,tipos):
    for titulo,crit in problemas:
     if db.query(ProblemaTipico).filter_by(id_tipo_ativo=tipo.id_tipo_ativo,titulo=titulo).first(): continue
     linha = "Linha de Transmissão" if grupo in {"CONDUTOR","ISOLADOR","TORRE","FUNDACAO","ATERRAMENTO","OPGW","FAIXA SERVIDAO","ACESSORIOS"} else "Subestação"
     p=ProblemaTipico(id_tipo_ativo=tipo.id_tipo_ativo,sistema=linha,categoria="Estrutural" if grupo in {"TORRE","FUNDACAO"} else "Elétrica",titulo=titulo,descricao=f"Condição típica: {titulo}.",criticidade_padrao=crit,detectabilidade="ALTA",especialidade="Linha de transmissão" if linha.startswith("Linha") else "Manutenção elétrica",requer_desligamento=crit=="CRITICA")
     p.sintomas=[SintomaProblema(sintoma=f"Indício de {titulo.lower()}"),SintomaProblema(sintoma="Alarme, medição ou inspeção fora do padrão")]
     p.causas=[CausaProblema(causa="Envelhecimento ou degradação do componente"),CausaProblema(causa="Condição operacional ou ambiental adversa")]
     p.acoes_recomendadas=[AcaoRecomendada(tipo_acao="INSPECAO",descricao="Inspecionar e registrar evidências"),AcaoRecomendada(tipo_acao="INVESTIGACAO",descricao="Confirmar causa e avaliar risco operacional")]
     p.metodos_deteccao=[MetodoDeteccaoProblema(metodo="Inspeção visual")]
     if titulo=="Gases anormais no óleo": p.metodos_deteccao=[MetodoDeteccaoProblema(metodo="DGA")]
     db.add(p); criados+=1
  db.commit(); print(f"Seed concluído: {criados} problemas criados.")
 finally: db.close()
if __name__=="__main__": main()
