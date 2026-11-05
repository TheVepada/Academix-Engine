from plyer import notification

def show_alert(title="Distraction Alert!", message="Task approaching! Focus back on work."):
    notification.notify(
        title=title,
        message=message,
        app_name="Academix",
        timeout=5
    )

if __name__ == "__main__":
    show_alert()