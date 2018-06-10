FROM python:2.7.14-jessie

ENV DEBIAN_FRONTEND noninteractive
ENV HASHCAT_VERSION hashcat-3.6.0

# Install requirements
RUN echo "deb-src http://deb.debian.org/debian jessie main" >> /etc/apt/sources.list
RUN apt-get update && apt-get upgrade -y
RUN apt-get install ca-certificates gcc openssl make kmod nano wget p7zip build-essential libsqlite3-dev libpcap0.8-dev libpcap-dev sqlite3 pkg-config libnl-genl-3-dev libssl-dev net-tools iw ethtool usbutils pciutils wireless-tools git curl wget unzip macchanger pyrit tshark -y
RUN apt-get build-dep aircrack-ng -y



#Install Aircrack from Source
RUN wget http://download.aircrack-ng.org/aircrack-ng-1.2-rc4.tar.gz
RUN tar xzvf aircrack-ng-1.2-rc4.tar.gz
WORKDIR /aircrack-ng-1.2-rc4/
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


# Install bully
RUN git clone https://github.com/aanarchyy/bully
WORKDIR /bully/src/
RUN make
RUN make install



# Workdir /
WORKDIR /

#Install and configure hashcat
RUN mkdir hashcat && \
    cd hashcat && \
    wget https://hashcat.net/files_legacy/${HASHCAT_VERSION}.7z && \
    7zr e ${HASHCAT_VERSION}.7z


#Add link for binary
RUN ln -s /hashcat/hashcat-cli64.bin /usr/bin/hashcat


# Install reaver
RUN git clone https://github.com/gabrielrcouto/reaver-wps.git
WORKDIR /reaver-wps/src/
RUN ./configure
RUN make
RUN make install

# Workdir /
WORKDIR /

# Install cowpatty
RUN git clone https://github.com/roobixx/cowpatty.git
WORKDIR /cowpatty/
RUN make

# Workdir /
WORKDIR /

# Install wifite
RUN git clone https://github.com/derv82/wifite2.git
WORKDIR /wifite2/
ENTRYPOINT ["/bin/bash"]


