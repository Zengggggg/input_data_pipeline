import uiautomation as auto

def get_active_url():
    try:
        class_name = auto.GetForegroundControl().ClassName
        browser_window = auto.WindowControl(searchDepth=1, ClassName=class_name)
        address_bar = browser_window.EditControl()

        return {
            "url": address_bar.GetValuePattern().Value,
            "title": browser_window.Name
        }
    except Exception as e:
        return {"error": str(e)}
    
def main():
    result = get_active_url()
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"URL: {result['url']}\nTitle: {result['title']}")

if __name__ == "__main__":
    main()