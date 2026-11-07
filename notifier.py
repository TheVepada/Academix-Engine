from plyer import notification

import subprocess

def show_alert(title="Distraction Alert!", message="Task approaching! Focus back on work."):
    app_id = "Academix Engine"
    
    # PowerShell script to call native Windows ToastNotificationManager
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $textNodes = $template.GetElementsByTagName("text")
    $textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null
    $textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}')
    $notification = [Windows.UI.Notifications.ToastNotification]::new($template)
    $notifier.Show($notification)
    """
    
    # Execute non-blocking without flashing a CMD window
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
        creationflags=subprocess.CREATE_NO_WINDOW
    )


if __name__ == "__main__":
    show_alert()