

# scons build
Set-Location "$buildRoot/test"
scons verbose=yes platform=android target=template_release arch=x86_64

# TODO Run test project
