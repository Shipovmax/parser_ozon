import json
import os
import re
import time

from DrissionPage import ChromiumOptions, ChromiumPage


def extract_ozon_id(url):
    """
    Вытаскивает цифровой ID товара из ссылки Ozon.
    Пример: из '...product/12345/...' достанет '12345'.
    """
    match = re.search(r"product/.*?(\d+)", url)
    return match.group(1) if match else "unknown"

def main():
    # Пути к файлам. Убедись, что папка существует.
    input_path = "/Users/shipov/Developer/123/test.txt"
    output_path = "/Users/shipov/Developer/123/ozon_prices.json"

    # --- Настройка «мозгов» браузера ---
    co = ChromiumOptions()
    
    # Пытаемся найти, где именно на Маке лежит Chrome
    chrome_path = "/Applications/Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_path):
        chrome_path = "/Applications/Chrome.app/Contents/MacOS/Chrome"

    co.set_browser_path(chrome_path)
    
    # ТУРБО-РЕЖИМ:
    co.no_imgs(True)         # Не грузим картинки — экономим кучу времени и трафика
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--mute-audio") # Чтобы внезапная реклама не орала из колонок
    
    # Запускаем сам браузер
    page = ChromiumPage(co)
    results = []

    try:
        # Проверка: есть ли вообще файл со ссылками
        if not os.path.exists(input_path):
            print(f"❌ Файл {input_path} не найден!")
            return

        # Читаем все ссылки из текстовика, убираем пустые строки
        with open(input_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]

        for url in urls:
            print(f"\n🚀 Летим на: {url}")
            p_id = extract_ozon_id(url)
            
            # РЕЖИМ ЖДУНА: 'eager' значит «не жди, пока прогрузится вся реклама и счетчики».
            # Нам нужен только скелет страницы, чтобы выдрать цену.
            page.set.load_mode.eager() 
            page.get(url)

            # ЗАЩИТА ОТ АНТИБОТА: если Ozon выкинул капчу
            if "captcha" in page.url or "verification" in page.url:
                print("🛑 Капча! Реши её руками в окне, скрипт поймет, когда ты закончишь...")
                # Ждем смены URL (когда капча пройдена), таймаут 100 секунд
                page.wait.url_change(timeout=100)

            price_found = None

            # СПИСОК ЦЕЛЕЙ: Ozon часто меняет дизайн, поэтому ищем цену в разных местах
            check_selectors = [
                "span.pdp_bj.tsHeadline600Large",   # Основная цена
                'div[data-widget="webPrice"] span', # Блок цены (старый/новый дизайн)
                'span[class*="tsHeadline600Large"]',# Поиск по частичному совпадению класса
                ".pdp_bj"                           # Запасной вариант
            ]

            # Пытаемся найти цену в течение 5 секунд (быстрыми итерациями)
            start_time = time.time()
            while time.time() - start_time < 5:
                for sel in check_selectors:
                    # timeout=0.1 — не тупим на каждом элементе, проверяем мгновенно
                    target = page.ele(f"css:{sel}", timeout=0.1) 
                    if target and target.text:
                        # Оставляем только цифры (убираем '₽', пробелы и т.д.)
                        digits = "".join(re.findall(r"\d+", target.text))
                        if digits:
                            price_found = digits
                            break
                if price_found:
                    break
                time.sleep(0.5) # Микро-пауза перед следующим кругом поиска

            # ХИТРЫЙ ПЛАН «Б»: если на странице визуально цену не нашли (дизайн-сюрприз)
            if not price_found:
                # Берем весь "внутренний мир" страницы (HTML код)
                raw_html = page.html
                # Ozon хранит данные в JSON-скриптах внутри страницы. Ищем там.
                json_price = re.search(r'"price":(\d+),', raw_html)
                if json_price:
                    price_found = json_price.group(1)
                    print("🔍 Цена вытянута из скрытых JSON данных страницы")

            if price_found:
                print(f"💰 Цена: {price_found}")
            else:
                print("❌ Цена не найдена (проверь, может товар закончился)")

            # Собираем результат в копилку
            results.append(
                {"id": p_id, "price": price_found or "Not Found", "url": url}
            )

    except KeyboardInterrupt:
        # Если ты нажал Ctrl+C, скрипт не сдохнет, а вежливо сохранится
        print("\n⏹ Парсинг остановлен тобой. Сохраняю всё, что нашел...")
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    finally:
        # В ЛЮБОМ СЛУЧАЕ (даже при ошибке) записываем данные в файл
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n🏁 Финиш! Результаты лежат здесь: {output_path}")
        # Закрываем браузер, чтобы не жрал оперативку
        page.quit()

if __name__ == "__main__":
    main()