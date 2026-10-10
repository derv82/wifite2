FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV HASHCAT_VERSION=hashcat-6.2.6
ENV HASHCAT_UTILS_VERSION=1.9

# Install all system dependencies in a single layer
RUN echo "deb http://deb.debian.org/debian trixie main" > /etc/apt/sources.list && \
    echo "deb-src http://deb.debian.org/debian trixie main" >> /etc/apt/sources.list && \
    apt update && \
    apt install -y --no-install-recommends \
        clang ca-certificates gcc openssl make kmod nano wget p7zip-full build-essential \
        libsqlite3-dev libpcap0.8-dev libpcap-dev sqlite3 pkg-config libnl-genl-3-dev \
        libssl-dev net-tools iw ethtool usbutils pciutils wireless-tools git curl libcurl3-dev unzip \
        macchanger tshark rfkill autoconf automake libtool && \
    apt build-dep -y aircrack-ng && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Install Aircrack from Source
RUN wget https://download.aircrack-ng.org/aircrack-ng-1.7.tar.gz && \
    tar xzvf aircrack-ng-1.7.tar.gz && \
    cd /aircrack-ng-1.7/ && \
    autoreconf -i && \
    ./configure --with-experimental && \
    make && make install && \
    airodump-ng-oui-update && \
    cd / && rm -rf /aircrack-ng-1.7 aircrack-ng-1.7.tar.gz

# Install pixiewps
RUN git clone https://github.com/wiire/pixiewps && \
    cd /pixiewps && make && make install && \
    cd / && rm -rf /pixiewps

# Install hcxdumptool
RUN git clone https://github.com/ZerBea/hcxdumptool.git && \
    cd /hcxdumptool && make && make install && \
    cd / && rm -rf /hcxdumptool

# Install hcxtools
RUN git clone https://github.com/ZerBea/hcxtools.git && \
    cd /hcxtools && make && make install && \
    cd / && rm -rf /hcxtools

# Install bully
RUN git clone https://github.com/kimocoder/bully && \
    cd /bully/src && make && make install && \
    cd / && rm -rf /bully

# Install and configure hashcat
RUN mkdir /hashcat && \
    cd /hashcat && \
    wget --no-check-certificate https://hashcat.net/files/${HASHCAT_VERSION}.7z && \
    7zr x ${HASHCAT_VERSION}.7z && \
    rm ${HASHCAT_VERSION}.7z && \
    wget https://github.com/hashcat/hashcat-utils/releases/download/v${HASHCAT_UTILS_VERSION}/hashcat-utils-${HASHCAT_UTILS_VERSION}.7z && \
    7zr x hashcat-utils-${HASHCAT_UTILS_VERSION}.7z && \
    rm hashcat-utils-${HASHCAT_UTILS_VERSION}.7z && \
    ln -s /hashcat/${HASHCAT_VERSION}/hashcat64.bin /usr/bin/hashcat && \
    ln -s /hashcat/hashcat-utils-${HASHCAT_UTILS_VERSION}/bin/cap2hccapx.bin /usr/bin/cap2hccapx

# Install reaver
RUN git clone https://github.com/t6x/reaver-wps-fork-t6x && \
    cd /reaver-wps-fork-t6x/src && ./configure && make && make install && \
    cd / && rm -rf /reaver-wps-fork-t6x

# Install cowpatty (with make install so binary is on PATH)
RUN git clone https://github.com/joswr1ght/cowpatty && \
    cd /cowpatty && make && make install && \
    cd / && rm -rf /cowpatty

# Install wifite and Python dependencies
RUN git clone https://github.com/kimocoder/wifite2.git && \
    chmod -R 777 /wifite2/

WORKDIR /wifite2/
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "wifite.py"]
