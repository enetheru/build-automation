# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/add-member?view=powershell-7.4
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_object_creation?view=powershell-7.4
# https://learn.microsoft.com/en-us/powershell/scripting/learn/deep-dives/everything-about-pscustomobject?view=powershell-7.4

function Beans {
    Write-Output "Beans, Beans,"
}

$configTemplate = [PSCustomObject]@{
    message = "The More You Eat"
}

$memberToAdd = @{
    MemberType  = 'ScriptMethod'
    Name        = 'Beans'
    Value       = ${Function:Beans}
}
$configTemplate | Add-Member @memberToAdd

Write-Output $configTemplate.Beans()

$memberToAdd = @{
    MemberType  = 'ScriptMethod'
    Name        = 'Beans'
    Value       = { Write-Output "The Musical Fruit" }
    Force       = $True
}
$configTemplate | Add-Member @memberToAdd

Write-Output $configTemplate.Beans()

Write-Output $configTemplate.message

$configTemplate.message = "The More You Toot"

Write-Output $configTemplate.message

function SheSells {
    Write-Output "Sea Shells"
}

$configCopy = $configTemplate.PSObject.Copy()

$memberToAdd = @{
    MemberType  = 'ScriptMethod'
    Name        = 'Beans'
    Value       = ${Function:SheSells}
    Force       = $True
}
[PSCustomObject]$configCopy | Add-Member @memberToAdd

$configCopy.Beans()
$configTemplate.Beans()