@ECHO OFF

:: %HOMEDRIVE% = C:
:: %HOMEPATH% = \Users\Ruben
:: %system32% ??
:: No spaces in paths
:: Program Files > ProgramFiles
:: cls = clear screen
:: CMD reads the system environment variables when it starts. To re-read those variables you need to restart CMD
:: Use console 2 http://sourceforge.net/projects/console/


:: Assign all Path variables
:: SET PHP="%HOMEDRIVE%\wamp\bin\php\php5.4.16"
:: SET SYSTEM32="%HOMEDRIVE%\Windows\System32"
:: SET ANT="%HOMEDRIVE%%HOMEPATH%\Downloads\apache-ant-1.9.0-bin\apache-ant-1.9.0\bin"
:: SET GRADLE="%HOMEDRIVE%\tools\gradle-1.6\bin;"
:: SET ADT="%HOMEDRIVE%\tools\adt-bundle-windows-x86-20130219\eclipse\jre\bin"
:: SET ADTTOOLS="%HOMEDRIVE%\tools\adt-bundle-windows-x86-20130219\sdk\tools"
:: SET ADTP="%HOMEDRIVE%\tools\adt-bundle-windows-x86-20130219\sdk\platform-tools"
:: SET YII="%HOMEDRIVE%\wamp\www\yii\framework"
:: SET NODEJS="%HOMEDRIVE%\ProgramFiles\nodejs"
:: SET CURL="%HOMEDRIVE%\tools\curl_734_0_ssl"
:: SET COMPOSER="%HOMEDRIVE%\ProgramData\ComposerSetup\bin"
:: SET GIT="%HOMEDRIVE%\Program Files\Git\cmd"

:: Set Path variable
::setx PATH "C:\mingw64\bin;%PATH%" /m
set "PATH=C:\mingw64\bin;%PATH%"

:: Set Java variable
:: setx JAVA_HOME "%HOMEDRIVE%\ProgramFiles\Java\jdk1.7.0_21" /m

::PAUSE
