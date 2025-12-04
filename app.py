import streamlit as st
import pandas as pd
from weasyprint import HTML
from io import BytesIO

# === Заголовок ===
st.set_page_config(page_title="Конфигуратор отчётов 360°", layout="centered")
st.title("🎯 Конфигуратор отчётов: Оценка 360°")
st.markdown("Загрузите Excel-файл из iSpring и настройте отчёт для встречи 1:1")

# === Загрузка файла ===
uploaded_file = st.file_uploader(
    "Загрузите файл в формате XLSX (экспорт из iSpring)",
    type=["xlsx"]
)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        # Проверка структуры
        required_cols = {"name", "department", "competency", "indicator", "self", "environment", "average"}
        if not required_cols.issubset(df.columns):
            st.error("❌ В файле должны быть колонки: name, department, competency, indicator, self, environment, average")
            st.stop()
        st.success("✅ Файл загружен. Найдено {} записей.".format(len(df)))
    except Exception as e:
        st.error(f"Ошибка при чтении файла: {e}")
        st.stop()

    # === Настройка порогов ===
    st.subheader("🔧 Настройка критериев")
    col1, col2 = st.columns(2)
    strong_min = col1.slider("Мин. средний балл для «сильной стороны»", 0.0, 3.0, 2.0, 0.1)
    strong_diff = col2.slider("Макс. расхождение для «сильной стороны»", 0.0, 3.0, 0.3, 0.1)
    dev_max = st.slider("Макс. средний балл для «зоны развития»", 0.0, 3.0, 1.5, 0.1)
    blind_min = st.slider("Мин. расхождение для «слепого пятна»", 0.0, 3.0, 0.8, 0.1)

    # === Выбор разделов ===
    st.subheader("챕 Разделы отчёта")
    col1, col2 = st.columns(2)
    with col1:
        include_strong = st.checkbox("🌟 Сильные стороны", True)
        include_dev = st.checkbox("🔸 Зоны развития", True)
        include_blind = st.checkbox("👀 Слепые пятна", True)
    with col2:
        include_hidden = st.checkbox("💡 Скрытые возможности", True)
        include_ipr = st.checkbox("🎯 Рекомендации для ИПР", True)
        include_sign = st.checkbox("📝 Блок подписей", True)

    # === Обработка по сотрудникам ===
    if st.button("🚀 Сгенерировать отчёт"):
        with st.spinner("Генерация PDF..."):
            # Обработка первого сотрудника (или можно по всем)
            first_row = df.iloc[0]
            name = first_row["name"]
            dept = first_row["department"]
            group = df[df["name"] == name].copy()

            # Классификация
            def classify(row):
                s, env, avg = row["self"], row["environment"], row["average"]
                diff = s - env
                if avg >= strong_min and abs(diff) <= strong_diff:
                    return "strong"
                elif avg < dev_max:
                    return "development"
                elif diff > blind_min:
                    return "blind_spot"
                elif diff < -0.5:
                    return "hidden"
                else:
                    return "other"

            group["category"] = group.apply(classify, axis=1)

            # Генерация HTML
            def to_list(items):
                if not items:
                    return "<p>— Не выявлено</p>"
                return "".join(f"<p style='margin: 4px 0;'>• {item}</p>" for item in items)

            strong = group[group["category"] == "strong"].apply(
                lambda x: f"{x['competency']}: «{x['indicator']}»", axis=1).tolist() if include_strong else []
            development = group[group["category"] == "development"].apply(
                lambda x: f"{x['competency']}: «{x['indicator']}»", axis=1).tolist() if include_dev else []
            blind = group[group["category"] == "blind_spot"].apply(
                lambda x: f"{x['competency']} (самооценка: {x['self']}, окружение: {x['environment']:.1f})", axis=1
            ).tolist() if include_blind else []
            hidden = ["Не определены. Нет областей, в которых оценка окружения значительно превышает самооценку."] if include_hidden else []

            ipr = []
            if include_ipr:
                for _, row in group[group["category"].isin(["development", "blind_spot"])].iterrows():
                    if row["category"] == "blind_spot":
                        ipr.append(f"• Обсудить завышенную самооценку по компетенции «{row['competency']}»")
                    else:
                        ipr.append(f"• Включить развитие компетенции «{row['competency']}» в ИПР")
                if not ipr:
                    ipr = ["• Текущий уровень компетенций достаточен. Рекомендуется делиться экспертизой."]

            html = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; font-size: 14px; line-height: 1.5; }}
                h1 {{ color: #2c3e50; text-align: center; margin-bottom: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin: 25px 0; }}
                h2 {{ color: #34495e; margin-top: 20px; }}
                p {{ margin: 6px 0; }}
                .footer {{ margin-top: 40px; font-style: italic; color: #7f8c8d; }}
            </style>
            </head>
            <body>
              <h1>Обратная связь: Оценка 360°</h1>
              <div class="header">
                <p><strong>Сотрудник:</strong> {name}</p>
                <p><strong>Подразделение:</strong> {dept}</p>
                <p><em>Цель встречи — обсудить результаты оценки 360°, определить сильные стороны, зоны роста и совместно сформировать ИПР.</em></p>
              </div>
            """
            if include_strong:
                html += f"<div class='section'><h2>🌟 Сильные стороны</h2>{to_list(strong)}</div>"
            if include_dev:
                html += f"<div class='section'><h2>🔸 Зоны развития</h2>{to_list(development)}</div>"
            if include_blind:
                html += f"<div class='section'><h2>👀 Слепые пятна</h2>{to_list(blind)}</div>"
            if include_hidden:
                html += f"<div class='section'><h2>💡 Скрытые возможности</h2>{to_list(hidden)}</div>"
            if include_ipr:
                html += f"<div class='section'><h2>🎯 Рекомендации для ИПР</h2>{to_list(ipr)}</div>"
            if include_sign:
                html += """
                <div class="footer">
                  <p>Обсуждено с руководителем: ___________________</p>
                  <p>Подпись сотрудника: _________________________</p>
                  <p>Дата: _______________________________________</p>
                </div>
                """
            html += "<div class='footer'>ДКС • Проект «Комплексная оценка» • 2025</div></body></html>"

            # Генерация PDF
            pdf_bytes = HTML(string=html).write_pdf()

            # Скачивание
            st.download_button(
                label="📥 Скачать PDF-отчёт",
                data=pdf_bytes,
                file_name=f"Обратная_связь_{name.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )