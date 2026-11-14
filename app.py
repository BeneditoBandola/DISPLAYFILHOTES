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

# --- ESTILIZAÇÃO DO TEMA (Branco, Preto e Vermelho) ---
st.markdown("""
    <style>
    /* Fundo branco e texto preto geral */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    /* Cor dos textos e títulos */
    h1, h2, h3, p, span, label {
        color: #000000 !important;
    }
    
    /* Estilização do Botão Principal (Vermelho) */
    div.stButton > button:first-child {
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #B71C1C !important;
        color: #FFFFFF !important;
    }
    
    /* Caixas de input e select */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #F5F5F5 !important;
        color: #000000 !important;
        border: 1px solid #CCCCCC !important;
    }
    
    /* Cor de sucesso e aviso adaptadas para ficar legíveis no fundo claro */
    div[data-testid="stSuccess"] {
        background-color: #E8F5E9 !important;
        color: #1B5E20 !important;
    }
    div[data-testid="stWarning"] {
        background-color: #FFF3E0 !important;
        color: #E65100 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. E-MAILS ---
EMAILS_FILIAIS = {
    "São João da Boa Vista": ["faturamentosjbv@minassal.com.br", "patricia.anunciacao@minassal.com.br"],
    "São José do Rio Preto": ["faturamentosjrp@minassal.com.br"],
    "Poços de Caldas": ["faturamentopc2@minassal.com.br"],
    "Juiz de Fora": ["faturamentojf@minassal.com.br"]
}
EMAIL_COPIA = "benedito.bandola@minassal.com.br"

@st.cache_data
def carregar_planilha():
    df = pd.read_csv("clientes base atualizado 14112026.csv", sep=None, engine='python', encoding='utf-8-sig')
    df.columns = df.columns.str.strip() 
    return df

def enviar_email_gmail(destinatarios, cc, assunto, nome_cliente, caminho_pdf):
    try:
        remetente = st.secrets["EMAIL_REMETENTE"]
        senha = st.secrets["SENHA_REMETENTE"]
        
        msg = MIMEMultipart('related')
        msg['From'] = remetente
        msg['To'] = ", ".join(destinatarios)
        if cc:
            msg['Cc'] = cc
        msg['Subject'] = assunto
        
        msg_alt = MIMEMultipart('alternative')
        msg.attach(msg_alt)
        
        hora_atual = datetime.now().hour
        saudacao = "Bom dia" if hora_atual < 12 else ("Boa tarde" if hora_atual < 18 else "Boa noite")
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
            <p>
              {saudacao},<br><br>
              Por favor, quando possível, vai ter um pedido para este cliente ({nome_cliente}), 
              poderia enviar o <b>display filhotes</b> com a carga por favor?<br><br>
              Obrigado!
            </p>
        """
        
        imagem_path = "display.png" if os.path.exists("display.png") else ("display.jpg" if os.path.exists("display.jpg") else None)
        
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
        if cc:
            todos_destinatarios.append(cc)
            
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, todos_destinatarios, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar: {e}")
        return False

# --- 2. GERADOR DO PDF ---
class ReciboPDF(FPDF):
    def criar_via(self, via, cliente, id_recibo, data_hora, filial):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, self.get_y(), w=30)
            
        self.set_font('Arial', 'B', 14)
        self.cell(0, 6, 'MINASSAL - DISTRIBUIDORA', ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'DESDE 1986', ln=True, align='C')
        self.ln(5)
        
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, f'Recibo de Material | ID: {id_recibo}', ln=True, align='C')
        self.cell(0, 8, via, ln=True, align='C')
        self.ln(2)
        
        nome = str(cliente['NOME']).strip().encode('latin-1', 'replace').decode('latin-1')
        endereco = str(cliente['ENDEREÇO']).strip().encode('latin-1', 'replace').decode('latin-1')
        bairro = str(cliente['BAIRRO']).strip().encode('latin-1', 'replace').decode('latin-1')
        cidade = str(cliente['CIDADE']).strip().encode('latin-1', 'replace').decode('latin-1')
        uf = str(cliente['UF']).strip()
        codigo = str(cliente['CÓDIGO']).strip()
        filial_formatada = filial.encode('latin-1', 'replace').decode('latin-1')
        
        self.set_font('Arial', 'B', 9)
        self.cell(0, 5, f'CLIENTE: {codigo} - {nome}', ln=True)
        
        self.set_font('Arial', '', 9)
        end_completo = f'ENDERECO: {endereco} - Bairro: {bairro} - {cidade}/{uf}'
        self.multi_cell(0, 5, end_completo)
        self.cell(0, 5, f'DATA: {data_hora} | FILIAL: {filial_formatada}', ln=True)
        self.ln(4)
        
        self.set_font('Arial', 'B', 9)
        self.cell(150, 7, 'MATERIAL', border=1)
        self.cell(40, 7, 'QTD', border=1, ln=True, align='C')
        
        self.set_font('Arial', '', 9)
        self.cell(150, 7, 'DISPLAY MINI CLIENTES - FILHOTES', border=1)
        self.cell(40, 7, '1', border=1, ln=True, align='C')
        self.ln(2)
        
        imagem_path = "display.png" if os.path.exists("display.png") else ("display.jpg" if os.path.exists("display.jpg") else None)
        if imagem_path:
            self.image(imagem_path, x=92, y=self.get_y(), w=25)
            self.ln(28) 
        else:
            self.ln(12)
        
        y = self.get_y()
        self.set_xy(10, y)
        self.cell(90, 5, '________________________________', align='C')
        self.set_xy(110, y)
        self.cell(90, 5, '________________________________', align='C', ln=True)
        
        self.set_xy(10, self.get_y())
        self.cell(90, 5, 'LOGISTICA MINASSAL', align='C')
        self.set_xy(110, self.get_y() - 5)
        self.cell(90, 5, 'ASSINATURA CLIENTE', align='C', ln=True)
        self.ln(8)
        
        self.set_draw_color(150, 150, 150)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_draw_color(0, 0, 0)
        self.ln(8)

# --- 3. INTERFACE DE "UM CLIQUE" ---
st.title("📦 Emissão Rápida - Display")

try:
    df_clientes = carregar_planilha()
except FileNotFoundError:
    st.error("O arquivo 'clientes base atualizado 14112026.csv' não foi encontrado.")
    st.stop()

# 1. Captura do Código
codigo_input = st.text_input("1. Digite o Código do Cliente (Apenas números):", placeholder="Ex: 17129")

# Só avança se algo for digitado
if codigo_input:
    if not codigo_input.isdigit():
        st.warning("⚠️ Digite apenas números no código.")
    else:
        codigo_int = int(codigo_input)
        cliente_linha = df_clientes[df_clientes['CÓDIGO'] == codigo_int]
        
        if cliente_linha.empty:
            st.error("❌ Cliente não encontrado. Verifique o código.")
        else:
            cliente = cliente_linha.iloc[0]
            nome_formatado_cliente = str(cliente["NOME"]).strip()
            
            # --- TELA DE CONFIRMAÇÃO DO CLIENTE ---
            st.success("✅ Cliente Encontrado!")
            with st.container():
                st.markdown(f"""
                **Nome:** {nome_formatado_cliente}  
                **Fantasia:** {cliente.get('NOME FANTASIA', '-')}  
                **Cidade:** {cliente.get('CIDADE', '-')} / {cliente.get('UF', '-')}  
                **Endereço:** {cliente.get('ENDEREÇO', '-')}, {cliente.get('BAIRRO', '-')}
                """)
            st.divider()

            # 2. Seleção de Filial e Modo Teste
            filial_selecionada = st.selectbox("2. Selecione a Filial:", list(EMAILS_FILIAIS.keys()))
            modo_teste = st.checkbox("🧪 Modo Teste (Enviar apenas para mim)", value=False)
            
            # 3. Botão de Envio
            if st.button("3. Gerar e Enviar E-mail 🚀"):
                # VERIFICAÇÃO ANTECIPADA DAS CREDENCIAIS
                if "EMAIL_REMETENTE" not in st.secrets or "SENHA_REMETENTE" not in st.secrets:
                    st.error("❌ Credenciais (Secrets) não cadastradas no Streamlit. Por favor, configure o arquivo secrets.toml ou as configurações do Streamlit Cloud.")
                else:
                    with st.spinner("Gerando recibo e disparando e-mail..."):
                        
                        pdf = ReciboPDF()
                        pdf.add_page()
                        agora = datetime.now()
                        data_hora = agora.strftime("%d/%m/%Y %H:%M")
                        id_recibo = agora.strftime("%y%m%d%H%M%S") 
                        
                        pdf.criar_via('VIA CLIENTE', cliente, id_recibo, data_hora, filial_selecionada)
                        pdf.criar_via('VIA MINASSAL', cliente, id_recibo, data_hora, filial_selecionada)
                        
                        nome_arquivo = f"Recibo_{codigo_int}.pdf"
                        pdf.output(nome_arquivo)
                        
                        assunto = f'Envio de display Royal Canin Mini filhotes para o cliente "{nome_formatado_cliente} e {cliente["CÓDIGO"]} / {cliente["CIDADE"]} / {cliente["UF"]}"'
                        
                        if modo_teste:
                            emails_para = [EMAIL_COPIA]
                            cc_email = None 
                        else:
                            emails_para = EMAILS_FILIAIS[filial_selecionada].copy()
                            email_cliente = str(cliente.get('E-MAIL', ''))
                            if email_cliente != 'nan' and email_cliente.strip() != '':
                                emails_para.append(email_cliente.strip())
                            cc_email = EMAIL_COPIA
                        
                        sucesso = enviar_email_gmail(emails_para, cc_email, assunto, nome_formatado_cliente, nome_arquivo)
                        if sucesso:
                            if modo_teste:
                                st.success(f"✅ MODO TESTE: Recibo gerado e e-mail enviado APENAS para {EMAIL_COPIA}.")
                            else:
                                st.success(f"✅ Prontinho! Recibo gerado e e-mail com imagem enviado com sucesso para a filial e para: {nome_formatado_cliente}.")
