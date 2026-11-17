import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders

st.set_page_config(page_title="Emissão Rápida", layout="centered")

# --- ESTILIZAÇÃO DO TEMA ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, p, label, .stMarkdown * { color: #000000 !important; }
    
    div[data-baseweb="select"] > div, input, textarea {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #CCCCCC !important;
    }
    
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[data-baseweb="menu-item"], li[data-baseweb="menu-item"] * { color: #000000 !important; }
    
    div.stButton > button { background-color: #D32F2F !important; border: none !important; font-weight: bold; }
    div.stButton > button * { color: #FFFFFF !important; }
    div.stButton > button:hover { background-color: #B71C1C !important; }
    div[data-testid="stCheckbox"] span { color: #000000 !important; font-weight: bold; }
    
    /* Ajuste para botões de rádio (Opções de Busca) */
    div[role="radiogroup"] label { color: #000000 !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE ALERTA PERSONALIZADAS ---
def alerta_sucesso(texto):
    st.markdown(f'<div style="background-color: #E8F5E9; padding: 12px; border-radius: 5px; border-left: 5px solid #4CAF50; color: #1B5E20; font-weight: bold; margin-bottom: 15px;">{texto}</div>', unsafe_allow_html=True)

def alerta_aviso(texto):
    st.markdown(f'<div style="background-color: #FFF3E0; padding: 12px; border-radius: 5px; border-left: 5px solid #FF9800; color: #E65100; font-weight: bold; margin-bottom: 15px;">{texto}</div>', unsafe_allow_html=True)

def alerta_erro(texto):
    st.markdown(f'<div style="background-color: #FFEBEE; padding: 12px; border-radius: 5px; border-left: 5px solid #F44336; color: #B71C1C; font-weight: bold; margin-bottom: 15px;">{texto}</div>', unsafe_allow_html=True)


# --- 1. E-MAILS E CONFIGURAÇÕES ---
EMAILS_FILIAIS = {
    "São João da Boa Vista": ["faturamentosjbv@minassal.com.br", "patricia.anunciacao@minassal.com.br"],
    "São José do Rio Preto": ["faturamentosjrp@minassal.com.br"],
    "Poços de Caldas": ["faturamentopc2@minassal.com.br"],
    "Juiz de Fora": ["faturamentojf@minassal.com.br"]
}

MEUS_EMAILS = [
    "beneditobandola@gmail.com",
    "benedito.bandola@minassal.com.br"
]

ARQUIVO_DISPLAYS = "displays.txt"

# --- FUNÇÕES DE CARREGAMENTO ---
@st.cache_data
def carregar_planilha():
    df = pd.read_csv("clientes base atualizado 14112026.csv", sep=None, engine='python', encoding='utf-8-sig')
    df.columns = df.columns.str.strip() 
    return df

def carregar_displays():
    displays_padrao = ["DISPLAY MINI CLIENTES - FILHOTES", "DISPLAY SLIM WET"]
    if not os.path.exists(ARQUIVO_DISPLAYS):
        # Cria o arquivo com os padrões se não existir
        with open(ARQUIVO_DISPLAYS, "w", encoding="utf-8") as f:
            f.write("\n".join(displays_padrao))
        return displays_padrao
    
    # Lê o arquivo
    with open(ARQUIVO_DISPLAYS, "r", encoding="utf-8") as f:
        return [linha.strip() for linha in f.readlines() if linha.strip()]

def salvar_novo_display(novo_display):
    with open(ARQUIVO_DISPLAYS, "a", encoding="utf-8") as f:
        f.write(f"\n{novo_display.strip().upper()}")

# --- FUNÇÃO DE ENVIO DE E-MAIL ---
def enviar_email_gmail(destinatarios, cc_list, assunto, nome_cliente, codigo_cliente, endereco_completo, caminho_pdf, tipo_display, observacao="", is_test=False):
    try:
        remetente = st.secrets["EMAIL_REMETENTE"]
        senha = st.secrets["SENHA_REMETENTE"]
        
        msg = MIMEMultipart('related')
        msg['From'] = remetente
        msg['To'] = ", ".join(destinatarios)
        if cc_list:
            msg['Cc'] = ", ".join(cc_list)
            
        if is_test:
            assunto = "[TESTE DO SISTEMA - IGNORAR] " + assunto
            
        msg['Subject'] = assunto
        
        msg_alt = MIMEMultipart('alternative')
        msg.attach(msg_alt)
        
        hora_atual = datetime.now().hour
        saudacao = "Bom dia" if hora_atual < 12 else ("Boa tarde" if hora_atual < 18 else "Boa noite")
        
        html = """<html><body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">"""
        
        if is_test:
            html += """
            <div style="background-color: #ffebee; border: 2px solid #b71c1c; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: #b71c1c; margin: 0;">⚠️ TESTE DE SISTEMA ⚠️</h2>
                <p style="color: #b71c1c; font-weight: bold; margin: 10px 0 0 0;">POR FAVOR, NÃO ENVIE NENHUM MATERIAL. ESTE É APENAS UM TESTE.</p>
            </div>
            """
            
        html += f"""
            <p>
              {saudacao},<br><br>
              Por favor, quando possível, vai ter um pedido para este cliente:<br>
              <b>{codigo_cliente} - {nome_cliente}</b><br>
              <b>Endereço de Entrega:</b> {endereco_completo}<br><br>
              Poderia enviar o <b>{tipo_display.lower()}</b> com a carga por favor?<br><br>
        """
        
        if observacao.strip():
            html += f"<p style='color: #D32F2F; font-weight: bold; border-left: 4px solid #D32F2F; padding-left: 10px;'>⚠️ Observação: {observacao}</p><br>"
            
        html += "Obrigado!</p>"
        
        # A imagem será inserida SOMENTE se o display for o de Filhotes
        imagem_path = None
        if tipo_display == "DISPLAY MINI CLIENTES - FILHOTES":
            if os.path.exists("display.png"):
                imagem_path = "display.png"
            elif os.path.exists("display.jpg"):
                imagem_path = "display.jpg"

        if imagem_path:
            html += '<br><img src="cid:img_display" style="max-width: 250px; border-radius: 8px; border: 1px solid #ccc;"><br>'
            
        html += "</body></html>"
        msg_alt.attach(MIMEText(html, 'html'))
        
        if imagem_path:
            with open(imagem_path, 'rb') as img_file:
                img_mime = MIMEImage(img_file.read())
                img_mime.add_header('Content-ID', '<img_display>')
                img_mime.add_header('Content-Disposition', 'inline')
                msg.attach(img_mime)
        
        with open(caminho_pdf, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(caminho_pdf)}"')
        msg.attach(part)
        
        todos_destinatarios = destinatarios.copy()
        if cc_list:
            todos_destinatarios.extend(cc_list)
            
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, todos_destinatarios, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        alerta_erro(f"❌ Erro ao enviar: {e}")
        return False

# --- 2. GERADOR DO PDF ---
class ReciboPDF(FPDF):
    def criar_via(self, via, cliente, id_recibo, data_hora, filial, tipo_display):
        y_start = self.get_y()
        
        caminho_logo = None
        if os.path.exists("logo.png"): caminho_logo = "logo.png"
        elif os.path.exists("logo.jpg"): caminho_logo = "logo.jpg"
        elif os.path.exists("logo.jpeg"): caminho_logo = "logo.jpeg"
        
        if caminho_logo:
            self.image(caminho_logo, x=10, y=y_start, w=35)
            
        self.set_xy(50, y_start)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 7, 'MINASSAL - DISTRIBUIDORA', ln=1)
        
        self.set_x(50)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'DESDE 1986', ln=1)
        
        self.set_x(50)
        self.set_font('Arial', '', 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 6, f'Recibo de Material | ID: {id_recibo}', ln=1)
        
        y_atual = self.get_y()
        y_apos_logo = y_start + 25 
        if y_atual < y_apos_logo:
            self.set_y(y_apos_logo)
        else:
            self.ln(2)
        
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 8, via, ln=1, align='C', fill=True)
        self.ln(4)
        
        nome = str(cliente['NOME']).strip().encode('latin-1', 'replace').decode('latin-1')
        endereco = str(cliente['ENDEREÇO']).strip().encode('latin-1', 'replace').decode('latin-1')
        bairro = str(cliente['BAIRRO']).strip().encode('latin-1', 'replace').decode('latin-1')
        cidade = str(cliente['CIDADE']).strip().encode('latin-1', 'replace').decode('latin-1')
        uf = str(cliente['UF']).strip()
        codigo = str(cliente['CÓDIGO']).strip()
        filial_formatada = filial.encode('latin-1', 'replace').decode('latin-1')
        end_completo = f'{endereco} - Bairro: {bairro} - {cidade}/{uf}'
        
        self.set_x(10)
        self.set_font('Arial', 'B', 10)
        self.cell(20, 6, 'CLIENTE:', ln=0)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, f'{codigo} - {nome}', ln=1)
        
        self.set_x(10)
        self.set_font('Arial', 'B', 10)
        self.cell(24, 6, 'ENDERECO:', ln=0)
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, end_completo)
        
        self.set_x(10)
        self.set_font('Arial', 'B', 10)
        self.cell(12, 6, 'DATA:', ln=0)
        self.set_font('Arial', '', 10)
        self.cell(40, 6, f'{data_hora}', ln=0)
        
        self.set_font('Arial', 'B', 10)
        self.cell(16, 6, 'FILIAL:', ln=0)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, f'{filial_formatada}', ln=1)
        
        self.ln(6)
        
        self.set_x(10)
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(200, 200, 200)
        self.cell(160, 8, ' MATERIAL', border=1, fill=True)
        self.cell(30, 8, 'QTD', border=1, ln=1, align='C', fill=True)
        
        self.set_x(10)
        self.set_font('Arial', 'B', 10)
        
        self.cell(160, 10, f' {tipo_display}', border=1)
        self.cell(30, 10, '1', border=1, ln=1, align='C')
        
        self.ln(25)
            
        y_ass = self.get_y()
        self.set_y(y_ass)
        self.set_x(10)
        
        self.set_font('Arial', '', 10)
        self.cell(85, 5, '______________________________________', align='C', ln=0)
        self.cell(20, 5, '', ln=0)
        self.cell(85, 5, '______________________________________', align='C', ln=1)
        
        self.set_x(10)
        self.set_font('Arial', 'B', 9)
        self.cell(85, 5, 'LOGISTICA MINASSAL', align='C', ln=0)
        self.cell(20, 5, '', ln=0)
        self.cell(85, 5, 'ASSINATURA CLIENTE', align='C', ln=1)


# --- 3. INTERFACE ---
st.title("📦 Emissão Rápida - Display")

if not os.path.exists("logo.png") and not os.path.exists("logo.jpg"):
    alerta_aviso("⚠️ O logotipo não foi encontrado no sistema. Suba um arquivo com o nome 'logo.png' ou 'logo.jpg' no GitHub para que ele apareça no PDF.")

try:
    df_clientes = carregar_planilha()
except FileNotFoundError:
    alerta_erro("❌ O arquivo de clientes não foi encontrado.")
    st.stop()

# --- SISTEMA DE BUSCA ---
cliente = None
codigo_int = None

st.subheader("1. Buscar Cliente")
tipo_busca = st.radio("Como deseja buscar?", ["Por Código", "Por Nome / Fantasia"], horizontal=True)

if tipo_busca == "Por Código":
    codigo_input = st.text_input("Digite o Código do Cliente (Apenas números):", placeholder="Ex: 17129")
    if codigo_input:
        if not codigo_input.isdigit():
            alerta_aviso("⚠️ Digite apenas números no código.")
        else:
            codigo_int = int(codigo_input)
            cliente_linha = df_clientes[df_clientes['CÓDIGO'] == codigo_int]
            if cliente_linha.empty:
                alerta_erro("❌ Cliente não encontrado. Verifique o código.")
            else:
                cliente = cliente_linha.iloc[0]

elif tipo_busca == "Por Nome / Fantasia":
    nome_input = st.text_input("Digite parte do Nome ou Fantasia:", placeholder="Ex: PET MANIA")
    if nome_input:
        mask = df_clientes['NOME'].astype(str).str.contains(nome_input, case=False, na=False) | \
               df_clientes['NOME FANTASIA'].astype(str).str.contains(nome_input, case=False, na=False)
        resultados = df_clientes[mask]
        
        if resultados.empty:
            alerta_erro("❌ Nenhum cliente encontrado com esse nome.")
        else:
            opcoes = ["-- Selecione o cliente na lista --"] + resultados.apply(lambda row: f"{row['CÓDIGO']} - {row['NOME']} ({row['CIDADE']}/{row['UF']})", axis=1).tolist()
            cliente_selecionado = st.selectbox("Selecione o cliente correto:", opcoes)
            
            if cliente_selecionado != "-- Selecione o cliente na lista --":
                codigo_int = int(cliente_selecionado.split(" - ")[0])
                cliente = df_clientes[df_clientes['CÓDIGO'] == codigo_int].iloc[0]

# --- PROCESSAMENTO APÓS ENCONTRAR O CLIENTE ---
if cliente is not None and codigo_int is not None:
    nome_formatado_cliente = str(cliente["NOME"]).strip()
    endereco_completo = f"{cliente.get('ENDEREÇO', '-')}, {cliente.get('BAIRRO', '-')} - {cliente.get('CIDADE', '-')} / {cliente.get('UF', '-')}"
    uf_cliente = str(cliente.get('UF', '')).strip().upper()
    
    alerta_sucesso("✅ Cliente Encontrado!")
    with st.container():
        st.markdown(f"""
        **Código:** {codigo_int}  
        **Nome:** {nome_formatado_cliente}  
        **Fantasia:** {cliente.get('NOME FANTASIA', '-')}  
        **UF:** {uf_cliente}  
        **Endereço Completo:** {endereco_completo}
        """)
    st.divider()

    st.subheader("2. Detalhes do Envio")
    
    # --- ÁREA DE CADASTRO E SELEÇÃO DE DISPLAYS ---
    lista_displays = carregar_displays()
    
    st.markdown("**Cadastrar Novo Material**")
    col1, col2 = st.columns([3, 1])
    with col1:
        novo_display_input = st.text_input("Nome do novo display/material:", label_visibility="collapsed", placeholder="Ex: DISPLAY NOVO MODELO", key="novo_display")
    with col2:
        if st.button("➕ Cadastrar", use_container_width=True):
            if novo_display_input:
                if novo_display_input.upper() not in lista_displays:
                    salvar_novo_display(novo_display_input)
                    st.success("Cadastrado com sucesso!")
                    st.rerun() # Atualiza a tela para mostrar o novo item
                else:
                    st.warning("Este item já existe!")
            else:
                st.warning("Digite um nome!")

    # Seletor dinâmico lendo da lista atualizada
    tipo_display_selecionado = st.radio("Selecione o material a enviar:", lista_displays)
    
    if tipo_display_selecionado == "DISPLAY MINI CLIENTES - FILHOTES" and not os.path.exists("display.png") and not os.path.exists("display.jpg"):
        alerta_aviso("⚠️ Imagem do display não encontrada. Suba um arquivo chamado 'display.png' no GitHub para resolver o e-mail.")

    if uf_cliente == 'MG':
        opcoes_filial = ["Juiz de Fora", "Poços de Caldas"]
    elif uf_cliente == 'SP':
        opcoes_filial = ["São João da Boa Vista", "São José do Rio Preto"]
    else:
        opcoes_filial = list(EMAILS_FILIAIS.keys())

    filial_selecionada = st.selectbox("Selecione a Filial de Faturamento:", opcoes_filial)
    
    observacao = st.text_input("📝 Observações para a logística (Opcional):", placeholder="Ex: Entregar apenas no período da tarde")
    
    # --- NOVAS OPÇÕES DE MODO DE ENVIO ---
    modo_envio = st.radio("Selecione o Modo de Envio:", [
        "🚀 Envio Real (Valendo)",
        "📢 Teste para a Filial (Para a filial - com aviso de IGNORAR)",
        "🔒 Teste Fechado (Só para mim - com aviso)"
    ])
    
    # --- LÓGICA DE DESTINATÁRIOS (DINÂMICA) ---
    emails_filial_base = EMAILS_FILIAIS[filial_selecionada].copy()
    cc_base = MEUS_EMAILS.copy()
    if filial_selecionada == "Poços de Caldas":
        cc_base.append("financeiro@minassal.com.br")
        
    if modo_envio == "🔒 Teste Fechado (Só para mim - com aviso)":
        display_to = MEUS_EMAILS.copy()
        display_cc = []
    else:
        display_to = emails_filial_base
        display_cc = cc_base
        
    # --- MOSTRADOR DE DESTINATÁRIOS NA TELA ---
    st.info(f"**Destinatários Principais (Para):**\n\n{', '.join(display_to)}\n\n**Em Cópia (CC):**\n\n{', '.join(display_cc) if display_cc else 'Nenhuma'}")
    
    if st.button("3. Gerar e Enviar E-mail"):
        if "EMAIL_REMETENTE" not in st.secrets or "SENHA_REMETENTE" not in st.secrets:
            alerta_erro("❌ Credenciais (Secrets) não cadastradas no Streamlit.")
        else:
            with st.spinner("Gerando recibo e disparando e-mail..."):
                
                pdf = ReciboPDF()
                
                pdf.add_page()
                agora = datetime.now()
                data_hora = agora.strftime("%d/%m/%Y %H:%M")
                id_recibo = agora.strftime("%y%m%d%H%M%S") 
                pdf.criar_via('VIA CLIENTE', cliente, id_recibo, data_hora, filial_selecionada, tipo_display_selecionado)
                
                pdf.add_page()
                pdf.criar_via('VIA MINASSAL', cliente, id_recibo, data_hora, filial_selecionada, tipo_display_selecionado)
                
                nome_arquivo = f"Recibo_{codigo_int}.pdf"
                pdf.output(nome_arquivo)
                
                assunto = f'Envio de {tipo_display_selecionado.lower()} para o cliente "{nome_formatado_cliente} - {endereco_completo}"'
                
                is_test = modo_envio != "🚀 Envio Real (Valendo)"
                
                sucesso = enviar_email_gmail(
                    destinatarios=display_to, 
                    cc_list=display_cc, 
                    assunto=assunto, 
                    nome_cliente=nome_formatado_cliente,
                    codigo_cliente=codigo_int,
                    endereco_completo=endereco_completo,
                    caminho_pdf=nome_arquivo, 
                    tipo_display=tipo_display_selecionado,
                    observacao=observacao, 
                    is_test=is_test
                )
                
                if sucesso:
                    if modo_envio == "🔒 Teste Fechado (Só para mim - com aviso)":
                        alerta_sucesso("✅ TESTE FECHADO: Recibo gerado e e-mail enviado APENAS para os seus e-mails.")
                    elif modo_envio == "📢 Teste para a Filial (Para a filial - com aviso de IGNORAR)":
                        alerta_sucesso(f"✅ TESTE PARA A FILIAL: E-mail enviado para ({filial_selecionada}) com o AVISO DE TESTE no assunto e corpo.")
                    else:
                        alerta_sucesso(f"✅ ENVIO REAL CONCLUÍDO! Recibo e e-mail enviados valendo para a filial ({filial_selecionada}).")
