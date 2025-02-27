# https://gist.github.com/dend/5ae8a70678e3a35d02ecd39c12f99110
# https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-notifications-overview
function Show-Notification {
    [cmdletbinding()]
    Param (
        [string]
        $ToastTitle,
        [string]
        [parameter(ValueFromPipeline)]
        $ToastText
    )
    
    #    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    
    $RawXml = [xml] $Template.GetXml()
    ($RawXml.toast.visual.binding.text | Where-Object {$_.id -eq "1"}).AppendChild($RawXml.CreateTextNode($ToastTitle)) > $null
    ($RawXml.toast.visual.binding.text | Where-Object {$_.id -eq "2"}).AppendChild($RawXml.CreateTextNode($ToastText)) > $null
    
    $SerializedXml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $SerializedXml.LoadXml($RawXml.OuterXml)
    
    $Toast = [Windows.UI.Notifications.ToastNotification]::new($SerializedXml)
    $Toast.Tag = "PowerShell"
    $Toast.Group = "PowerShell"
    $Toast.ExpirationTime = [DateTimeOffset]::Now.AddMinutes(1)
    
    $Notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("PowerShell")
    $Notifier.Show($Toast);
}


# https://stackoverflow.com/questions/47115811/how-to-keep-powershell-notification-in-action-center/47123275#47123275
[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")

$objNotifyIcon = New-Object System.Windows.Forms.NotifyIcon
while($True)
{
    $objNotifyIcon.Icon = [System.Drawing.SystemIcons]::Information
    $objNotifyIcon.BalloonTipIcon = "Info"
    $objNotifyIcon.BalloonTipTitle = "wzzup this is a title."
    $objNotifyIcon.BalloonTipText = "WHATS UPPP THIS IS A PARAGRAPH!"
    $objNotifyIcon.Visible = $True
    $objNotifyIcon.ShowBalloonTip(10000)
    Start-Sleep 500
}