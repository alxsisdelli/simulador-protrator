import streamlit as st
from datetime import date, timedelta
from fpdf import FPDF

# --- CONFIGURAÇÕES E REGRAS DO PROGRAMA ---
TAXA_SELIC = 0.15
LIMITE_TAXA_SUBVENCAO = 0.08
LIMITE_VALOR_SUBSIDIO = 50000.00
TAXA_IOF_ADICIONAL = 0.0038

# --- FUNÇÕES DE CÁLCULO ---
def formatar_moeda(valor):
    """Formata um número para o padrão de moeda brasileiro (R$)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_financiamento_sac(valor_operacao, taxa_juros_anual, num_parcelas, data_liberacao, vencimento_1a_parcela):
    cronograma = []
    saldo_devedor = valor_operacao
    
    if num_parcelas <= 0:
        return [], 0
        
    amortizacao_constante = valor_operacao / num_parcelas
    
    for i in range(1, num_parcelas + 1):
        if i == 1:
            dias_primeiro_periodo = (vencimento_1a_parcela - data_liberacao).days
            juros_periodo = saldo_devedor * (taxa_juros_anual / 365.0) * dias_primeiro_periodo
        else:
            juros_periodo = saldo_devedor * taxa_juros_anual

        valor_parcela = amortizacao_constante + juros_periodo
        saldo_devedor -= amortizacao_constante
        
        if abs(saldo_devedor) < 0.01:
            saldo_devedor = 0

        cronograma.append({
            "Parcela": i, "Valor da Parcela": valor_parcela, "Juros": juros_periodo,
            "Amortização": amortizacao_constante, "Saldo Devedor": saldo_devedor
        })
        
    total_juros_pago = sum(p['Juros'] for p in cronograma)
    return cronograma, total_juros_pago


# --- FUNÇÃO GERADORA DE PDF (AJUSTADA) ---
class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Simulador de Financiamento Pró-Trator', border=0, ln=1, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', border=0, align='C')

def criar_pdf(dados):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, '1. Resumo da Operação', ln=1)
    pdf.set_font('helvetica', '', 10)
    # AJUSTE: Adicionada a linha do IOF Adicional
    pdf.multi_cell(0, 8,
        f"Valor Solicitado: {dados['valor_formatado']}\n"
        f"Taxa de Juros: {dados['taxa_pct']}% a.a.\n"
        f"Prazo do Financiamento: {dados['num_parcelas']} anos\n"
        f"Data de Liberação: {dados['data_liberacao']}\n"
        f"Vencimento da 1ª Parcela: {dados['vencimento_1a_parcela']}\n"
        f"IOF Adicional (0,38%): {dados['iof_formatado']}",
        border=1, ln=1
    )
    pdf.ln(5)
    
    # Tabela 1: Simulação Original
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, '2. Simulação Original (Sem Subsídio)', ln=1)
    pdf.set_font('helvetica', '', 10)
    pdf.set_fill_color(230, 230, 230)
    col_widths = [20, 40, 35, 40, 45]
    headers = ['Parcela', 'Valor da Parcela', 'Juros', 'Amortização', 'Saldo Devedor']
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, align='C', fill=True)
    pdf.ln()
    for linha in dados['cronograma_original']:
        pdf.cell(col_widths[0], 8, str(linha['Parcela']), border=1, align='C')
        pdf.cell(col_widths[1], 8, formatar_moeda(linha['Valor da Parcela']), border=1, align='R')
        pdf.cell(col_widths[2], 8, formatar_moeda(linha['Juros']), border=1, align='R')
        pdf.cell(col_widths[3], 8, formatar_moeda(linha['Amortização']), border=1, align='R')
        pdf.cell(col_widths[4], 8, formatar_moeda(linha['Saldo Devedor']), border=1, align='R')
        pdf.ln()
    # AJUSTE: Adicionada a linha de totais
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(col_widths[0], 8, 'TOTAL', border=1, align='C', fill=True)
    pdf.cell(col_widths[1], 8, dados['total_parcela_orig_f'], border=1, align='R', fill=True)
    pdf.cell(col_widths[2], 8, dados['total_juros_orig_f'], border=1, align='R', fill=True)
    pdf.cell(col_widths[3], 8, dados['total_amort_orig_f'], border=1, align='R', fill=True)
    pdf.cell(col_widths[4], 8, '-', border=1, align='C', fill=True)
    pdf.ln(10)

    # Tabela 2: Resultado Final
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, '3. Resultado Final com Subsídio', ln=1)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(28, 131, 29)
    pdf.cell(0, 10, f"VALOR TOTAL DO SUBSÍDIO APLICADO: {formatar_moeda(dados['subsidio_final'])}", ln=1, align='C', fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font('helvetica', '', 10)
    pdf.set_fill_color(230, 230, 230)
    headers_final = ['Parcela', 'Parcela Original', 'Redução (Subsídio)', 'PARCELA FINAL']
    col_widths_final = [20, 50, 50, 60]
    for i, header in enumerate(headers_final):
        pdf.cell(col_widths_final[i], 8, header, border=1, align='C', fill=True)
    pdf.ln()
    for linha in dados['tabela_final']:
        pdf.cell(col_widths_final[0], 8, str(linha['Parcela']), border=1, align='C')
        pdf.cell(col_widths_final[1], 8, formatar_moeda(linha['Parcela Original']), border=1, align='R')
        pdf.cell(col_widths_final[2], 8, formatar_moeda(linha['Redução (Subsídio)']), border=1, align='R')
        pdf.cell(col_widths_final[3], 8, formatar_moeda(linha['PARCELA FINAL']), border=1, align='R')
        pdf.ln()
    # AJUSTE: Adicionada a linha de totais
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(col_widths_final[0], 8, 'TOTAL', border=1, align='C', fill=True)
    pdf.cell(col_widths_final[1], 8, dados['total_parcela_orig_f'], border=1, align='R', fill=True)
    pdf.cell(col_widths_final[2], 8, formatar_moeda(dados['subsidio_final']), border=1, align='R', fill=True)
    pdf.cell(col_widths_final[3], 8, dados['total_parcela_final_f'], border=1, align='R', fill=True)
    
    return bytes(pdf.output())


# --- INTERFACE DA APLICAÇÃO WEB ---
st.set_page_config(page_title="Simulador Pró-Trator", layout="wide")
st.title("Simulador de Financiamento Pró-Trator 🚜")

with st.sidebar:
    st.header("Informações da Operação")
    valor_operacao = st.number_input("Valor da Operação (R$)", min_value=1000.0, value=150000.0, step=1000.0)
    taxa_juros_anual_pct = st.number_input("Taxa de Juros ao Ano (%)", min_value=0.1, value=10.5, step=0.1)
    num_parcelas = st.number_input("Prazo do Financiamento (em anos)", min_value=1, max_value=20, value=7, step=1)
    data_liberacao = st.date_input("Data de Liberação do Crédito", value=date.today())
    vencimento_1a_parcela = st.date_input("Vencimento da 1ª Parcela", value=(date.today() + timedelta(days=365)))
    calcular_btn = st.button("Calcular Simulação")

if data_liberacao >= vencimento_1a_parcela:
    st.error("O 'Vencimento da 1ª Parcela' deve ser posterior à 'Data de Liberação'.")
elif calcular_btn:
    taxa_juros_anual = taxa_juros_anual_pct / 100.0
    
    st.header("1. Resumo da Operação", divider='gray')
    with st.container(border=True):
        st.markdown(f"**Valor Solicitado:** {formatar_moeda(valor_operacao)}")
        st.markdown(f"**Taxa de Juros:** {taxa_juros_anual_pct}% a.a.")
        st.markdown(f"**Prazo:** {num_parcelas} anos")
        st.markdown(f"**Data de Liberação:** {data_liberacao.strftime('%d/%m/%Y')}")
        st.markdown(f"**Vencimento da 1ª Parcela:** {vencimento_1a_parcela.strftime('%d/%m/%Y')}")
    
    st.header("2. Simulação Original (Sem Subsídio)", divider='blue')
    cronograma_original, total_juros_original = calcular_financiamento_sac(
        valor_operacao, taxa_juros_anual, num_parcelas, data_liberacao, vencimento_1a_parcela
    )
    
    st.dataframe(cronograma_original, hide_index=True, column_config={
        "Valor da Parcela": st.column_config.NumberColumn(format="R$ %.2f"), "Juros": st.column_config.NumberColumn(format="R$ %.2f"),
        "Amortização": st.column_config.NumberColumn(format="R$ %.2f"), "Saldo Devedor": st.column_config.NumberColumn(format="R$ %.2f")})
    
    iof_adicional = valor_operacao * TAXA_IOF_ADICIONAL
    col1, col2 = st.columns(2)
    col1.metric("Total de Juros na Simulação", value=formatar_moeda(total_juros_original))
    col2.metric("IOF Adicional (0,38%)", value=formatar_moeda(iof_adicional))

    taxa_subvencao_potencial = TAXA_SELIC * 0.5
    taxa_subvencao_efetiva = min(taxa_subvencao_potencial, LIMITE_TAXA_SUBVENCAO)
    taxa_juros_anual_subsidiada = max(0, taxa_juros_anual - taxa_subvencao_efetiva)
    
    _, total_juros_subsidiado = calcular_financiamento_sac(
        valor_operacao, taxa_juros_anual_subsidiada, num_parcelas, data_liberacao, vencimento_1a_parcela
    )
    
    subsidio_calculado = total_juros_original - total_juros_subsidiado
    subsidio_final = min(subsidio_calculado, LIMITE_VALOR_SUBSIDIO)
    
    st.success(f"**VALOR TOTAL DO SUBSÍDIO APLICADO: {formatar_moeda(subsidio_final)}**")
    
    st.header("3. Resultado Final", divider='orange')
    reducao_por_parcela = subsidio_final / num_parcelas
    
    tabela_final = []
    for p in cronograma_original:
        tabela_final.append({
            "Parcela": p['Parcela'], "Parcela Original": p['Valor da Parcela'],
            "Redução (Subsídio)": reducao_por_parcela, "PARCELA FINAL": p['Valor da Parcela'] - reducao_por_parcela
        })
    st.dataframe(tabela_final, hide_index=True, column_config={
        "Parcela Original": st.column_config.NumberColumn(format="R$ %.2f"), "Redução (Subsídio)": st.column_config.NumberColumn(format="R$ %.2f"),
        "PARCELA FINAL": st.column_config.NumberColumn(format="R$ %.2f")})

    st.markdown("---")
    
    # AJUSTE: Calculando e coletando todos os totais para o PDF
    total_parcela_orig = sum(p['Valor da Parcela'] for p in cronograma_original)
    total_amort_orig = sum(p['Amortização'] for p in cronograma_original)
    total_parcela_final = sum(p['PARCELA FINAL'] for p in tabela_final)
    
    dados_para_pdf = {
        "valor_formatado": formatar_moeda(valor_operacao),
        "iof_formatado": formatar_moeda(iof_adicional),
        "taxa_pct": taxa_juros_anual_pct,
        "num_parcelas": num_parcelas,
        "data_liberacao": data_liberacao.strftime('%d/%m/%Y'),
        "vencimento_1a_parcela": vencimento_1a_parcela.strftime('%d/%m/%Y'),
        "cronograma_original": cronograma_original,
        "subsidio_final": subsidio_final,
        "tabela_final": tabela_final,
        # Passando os totais formatados para o PDF
        "total_parcela_orig_f": formatar_moeda(total_parcela_orig),
        "total_juros_orig_f": formatar_moeda(total_juros_original),
        "total_amort_orig_f": formatar_moeda(total_amort_orig),
        "total_parcela_final_f": formatar_moeda(total_parcela_final),
    }
    
    pdf_bytes = criar_pdf(dados_para_pdf)
    
    st.download_button(
        label="📄 Gerar PDF", data=pdf_bytes, file_name=f"simulacao_{valor_operacao:.0f}.pdf", mime="application/pdf"
    )

else:
    st.info("Preencha os dados na barra lateral e clique em 'Calcular Simulação' para começar.")
