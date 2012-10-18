#Obtaining source
#git clone git://github.com/smolleyes/gmediafinder.git && tar cjf gmediafinder-{_version}.tar.bz2 gmediafinder/ && rm -rf gmediafinder
Name:			gmediafinder
Version:		1.0.3
Release:		2
Summary:		Stream and/or download and/or convert files
License:		GPLv2
Group:			Video
URL:			http://gnomefiles.org/content/show.php/Gmediafinder?content=138588&PHPSESSID=9c909890a42ce1ac7a555efab2b34b83
Source0:		https://nodeload.github.com/smolleyes/gmediafinder2/%{name}-%{version}.tar.gz
BuildRequires:		hicolor-icon-theme 
BuildRequires:		python-mechanize 
BuildRequires:		python-setuptools 
BuildRequires:		python-distutils-extra 
BuildRequires:		intltool
BuildRequires:		python-gdata
BuildRequires:		python-configobj
BuildRequires:		gettext

Requires:		gnome-icon-theme 
Requires:		pythonegg(html5lib)
Requires:		gstreamer0.10-python 
Requires:		gstreamer0.10-ffmpeg 
Requires:		gstreamer0.10-plugins-good 
Requires:		python-gdata 
Requires:		pygtk2.0 
Requires:		python-mechanize 
Requires:		libffmpeg 
Requires:		pythonegg(python-xlib)
Requires:		gstreamer0.10-tools
Requires:		%{_lib}avutil50
Requires:		gstreamer0.10-libvisual 
Requires:		libvisual-plugins 
Requires:		python-configobj 
Requires:		pygtk2.0-libglade
BuildArch:		noarch


%description
Gmediafinder is a software to search stream an/or download files 
form you-tube without flash,
Google and some mp3 search-engines (you know the rules...)
its support full-screen mode, visualization and use the gstreamer engine
for you-tube you can select your preferred, resolution and give priority to 
mp4 format for video seeking! (and lower CPU usage than flv...).


%prep
%setup -q 
%__chmod 644 CHANGELOG gpl-2.0.txt README VERSION


%build
python setup.py build 

%install
%__python setup.py install --root=%{buildroot}
cp -R data/img/throbber.png %{buildroot}%{_datadir}/%{name}/
%__chmod 644 %{buildroot}%{_datadir}/applications/%{name}.desktop
%__chmod 644 %{buildroot}%{_datadir}/%{name}/*.png
%__chmod 644 %{buildroot}%{_datadir}/%{name}/*/*
%__chmod a+x %{buildroot}%{_datadir}/pyshared/GmediaFinder/lib/engines/__init__.py
%__chmod a+x %{buildroot}%{_datadir}/pyshared/GmediaFinder/__init__.py
%__chmod a+x %{buildroot}%{_datadir}/pyshared/GmediaFinder/lib/__init__.py

%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/Translation.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/__init__.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/engines/__init__.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/downloads/__init__.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/__init__.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/player/__init__.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/engines/main.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/get_stream.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/gmediafinder.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/pykey.py
%__chmod a+x %{buildroot}%{py_sitedir}/GmediaFinder/lib/checklinks.py
%__chmod a+x %{buildroot}%{_datadir}/gmediafinder/scripts/get_stream.py 



desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop

%find_lang %{name} 

%files -f %{name}.lang

%doc CHANGELOG gpl-2.0.txt README VERSION
%{_bindir}/*
%{_datadir}/applications/%{name}.desktop
%{py_sitedir}/*/*
%{_datadir}/%{name}/*
%{_iconsdir}/hicolor/*/apps/%{name}.png
%{_datadir}/pyshared/GmediaFinder/*





