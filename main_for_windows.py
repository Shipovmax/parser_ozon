import json
import os
import re
import time

from DrissionPage import ChromiumOptions, ChromiumPage

def extract_ozon_id(url):
    match = re.search(r"product/.*?(\d+)", url)
    return match.group(1) if match else "unknown"

def main():
    # Использование относительных путей, чтобы работало на любой папке в Windows
    # Скрипт будет искать test.txt в той же папке, где лежит сам .py файл
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "test.txt")
    output_path = os.path.join(base_dir, "ozon_prices.json")

    co = ChromiumOptions()
    
    # --- Настройка для Windows ---
    # В 99% случаев DrissionPage на Windows сама находит Chrome.
    # Если Chrome установлен не в стандартную папку, раскомментируй строку ниже:
    # co.set_browser_path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    
    co.no_imgs(True)
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--mute-audio")
    
    page = ChromiumPage(co)
    results = []

    try:
        if not os.path.exists(input_path):
            print(f"❌ Файл не найден: {input_path}")
            print("Создай файл test.txt со ссылками в папке со скриптом.")
            return

        with open(input_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]

        for url in urls:
            print(f"\n🚀 Парсим: {url}")
            p_id = extract_ozon_id(url)
            
            page.set.load_mode.eager() 
            page.get(url)

            if "captcha" in page.url or "verification" in page.url:
                print("🛑 Вылезла капча! Реши её в открытом окне браузера...")
                page.wait.url_change(timeout=100)

            price_found = None
            check_selectors = [
                "span.pdp_bj.tsHeadline600Large",
                'div[data-widget="webPrice"] span',
                'span[class*="tsHeadline600Large"]',
                ".pdp_bj"
            ]

            start_time = time.time()
            while time.time() - start_time < 5:
                for sel in check_selectors:
                    target = page.ele(f"css:{sel}", timeout=0.1) 
                    if target and target.text:
                        digits = "".join(re.findall(r"\d+", target.text))
                        if digits:
                            price_found = digits
                            break
                if price_found:
                    break
                time.sleep(0.5)

            if not price_found:
                raw_html = page.html
                json_price = re.search(r'"price":(\d+),', raw_html)
                if json_price:
                    price_found = json_price.group(1)
                    print("🔍 Цена найдена в JSON")

            if price_found:
                print(f"💰 Цена: {price_found}")
            else:
                print("❌ Цена не найдена")

            results.append({"id": p_id, "price": price_found or "Not Found", "url": url})

    except KeyboardInterrupt:
        print("\n⏹ Остановлено пользователем.")
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    finally:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n🏁 Готово! Результаты в файле: {output_path}")
        page.quit()

if __name__ == "__main__":
    main()