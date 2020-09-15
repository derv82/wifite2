FROM python:2.7.14-jessie

ENV DEBIAN_FRONTEND noninteractive
ENV HASHCAT_VERSION hashcat-5.1.0
ENV HASHCAT_UTILS_VERSION  1.9

# Install requirements
RUN echo "deb-src http://deb.debian.org/debian jessie main" >> /etc/apt/sources.list
RUN apt update && apt upgrade -y
RUN apt install clang ca-certificates gcc openssl make kmod nano wget p7zip build-essential libsqlite3-dev libpcap0.8-dev libpcap-dev sqlite3 pkg-config libnl-genl-3-dev libssl-dev net-tools iw ethtool usbutils pciutils wireless-tools git curl wget unzip macchanger pyrit tshark -y
RUN apt build-dep aircrack-ng -y

# Install Aircrack from Source
RUN wget https://download.aircrack-ng.org/aircrack-ng-1.6.tar.gz
RUN tar xzvf aircrack-ng-1.6.tar.gz
WORKDIR /aircrack-ng-1.6/
RUN autoreconf -i
RUN ./configure --with-experimental
RUN make
RUN make install
RUN airodump-ng-oui-update

# Workdir /
WORKDIR /

# Install wps-pixie
RUN git clone https://github.com/wiire/pixiewps
WORKDIR /pixiewps/
RUN make
RUN make install

# Workdir /
WORKDIR /

# Install hcxdump
RUN git clone https://github.com/ZerBea/hcxdumptool.git
WORKDIR /hcxdumptool/
RUN make
RUN make install

# Workdir /
WORKDIR /

# Install hcxtools
RUN git clone https://github.com/ZerBea/hcxtools.git
WORKDIR /hcxtools/
RUN make
RUN make install

# Workdir /
WORKDIR /

# Install bully
RUN git clone https://github.com/aanarchyy/bully
WORKDIR /bully/src/
RUN make
RUN make install

# Workdir /
WORKDIR /

# Install and configure hashcat
RUN mkdir /hashcat

# Install and configure hashcat: it's either the latest release or in legacy files
RUN cd /hashcat && \
    wget --no-check-certificate https://hashcat.net/files/${HASHCAT_VERSION}.7z && \
    7zr x ${HASHCAT_VERSION}.7z && \
    rm ${HASHCAT_VERSION}.7z

RUN cd /hashcat && \
    wget https://github.com/hashcat/hashcat-utils/releases/download/v${HASHCAT_UTILS_VERSION}/hashcat-utils-${HASHCAT_UTILS_VERSION}.7z && \
    7zr x hashcat-utils-${HASHCAT_UTILS_VERSION}.7z && \
    rm hashcat-utils-${HASHCAT_UTILS_VERSION}.7z

# Add link for binary
RUN ln -s /hashcat/${HASHCAT_VERSION}/hashcat64.bin /usr/bin/hashcat
RUN ln -s /hashcat/hashcat-utils-${HASHCAT_UTILS_VERSION}/bin/cap2hccapx.bin /usr/bin/cap2hccapx

# Workdir /
WORKDIR /

# Install reaver
RUN git clone https://github.com/t6x/reaver-wps-fork-t6x
WORKDIR /reaver-wps-fork-t6x/src/
RUN ./configure
RUN make
RUN make install

# Workdir /
WORKDIR /

# Install cowpatty
RUN git clone https://github.com/joswr1ght/cowpatty
WORKDIR /cowpatty/
RUN make

# Workdir /
WORKDIR /

# Install wifite
RUN git clone https://github.com/kimocoder/wifite2.git
RUN chmod -R 777 /wifite2/
WORKDIR /wifite2/
RUN apt install rfkill -y
ENTRYPOINT ["/bin/bash"]
