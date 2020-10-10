SET(CMAKE_C_COMPILER_WORKS 1)

CMAKE_MINIMUM_REQUIRED(VERSION 2.6)
PROJECT(ath9k_firmware NONE)
ENABLE_LANGUAGE(C)

ADD_DEFINITIONS(-g -Os -Wunused-label -Wunused-variable -Wunused-value -Wpointer-arith -Wundef -nostdlib -Wundef)
ADD_DEFINITIONS(
	-D_RAM_
	-DBIG_ENDIAN -D_BYTE_ORDER=_BIG_ENDIAN
	-D__XTENSA__
	-DFUSION_USB_FW -DRX_SCATTER
	-DFUSION_USB_ENABLE_TX_STREAM -DFUSION_USB_ENABLE_RX_STREAM
	-DATH_ENABLE_CABQ
)

SET(SOURCES
	magpie_fw_dev/target/init/app_start.c
	magpie_fw_dev/target/init/init.c
	magpie_fw_dev/target/init/magpie.c
	magpie_fw_dev/target/adf/adf_nbuf.c
	magpie_fw_dev/target/adf/adf_net.c
	magpie_fw_dev/target/adf/adf_os_defer_pvt.c
	magpie_fw_dev/target/adf/adf_os_dma.c
	magpie_fw_dev/target/adf/adf_os_irq_pvt.c
	magpie_fw_dev/target/adf/adf_os_timer.c
	magpie_fw_dev/target/buf_pool/buf_pool_static.c
	magpie_fw_dev/target/cmnos/dbg_api.c
	magpie_fw_dev/target/cmnos/cmnos_sflash.c
	magpie_fw_dev/target/hif/usb_api_main_patch.c
	wlan/ah.c
	wlan/ah_osdep.c
	wlan/ar5416Phy.c
	wlan/ar5416_hw.c
	wlan/ar5416_phy.c
	wlan/ratectrl_11n_ln.c
	wlan/if_owl.c
	wlan/if_ath.c
	wlan/if_ath_pci.c
	wlan/debug.c
	wlan/attacks.c
	magpie_fw_dev/target/wlan/wlan_pci.c
	wlan/ieee80211_output.c
	magpie_fw_dev/target/htc/htc.c
	magpie_fw_dev/target/wmi/wmi_svc.c
)

IF(TARGET_K2)
	SET(SOURCES ${SOURCES}
		magpie_fw_dev/target/hif/k2_HIF_usb_patch.c
		magpie_fw_dev/target/hif/usb_api_k2_patch.c
	)
	SET(LIBS ${LIBS} hif)
	ADD_DEFINITIONS(-DPROJECT_K2)
	SET(PLATFORM_NAME k2)
	SET(SOURCES ${SOURCES}
		magpie_fw_dev/target/cmnos/k2_cmnos_clock_patch.c
		magpie_fw_dev/target/cmnos/k2_fw_cmnos_printf.c
	)
	SET(FIRMWARE_NAME htc_9271.fw)
ELSEIF(TARGET_MAGPIE)
	ADD_DEFINITIONS(
		-DROM_VER_1_1 -D_ROM_1_1_
		-DPROJECT_MAGPIE
		-DMAGPIE_MERLIN
	)
	SET(SOURCES ${SOURCES}
		magpie_fw_dev/target/hif/usb_api_magpie_patch.c
		magpie_fw_dev/target/rompatch/cmnos_clock_patch.c
		magpie_fw_dev/target/rompatch/HIF_usb_patch.c
	)
	INCLUDE_DIRECTORIES(
		${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/adf
	)
	SET(PLATFORM_NAME magpie)
	SET(FIRMWARE_NAME htc_7010.fw)
ELSE()
	MESSAGE(FATAL_ERROR "Unknown target name")
ENDIF()

INCLUDE_DIRECTORIES(
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/inc
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/inc/xtensa-elf
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/inc/${PLATFORM_NAME}
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/inc/${PLATFORM_NAME}/${PLATFORM_NAME}
	${CMAKE_SOURCE_DIR}/wlan
	${CMAKE_SOURCE_DIR}/wlan/include
	${CMAKE_SOURCE_DIR}/wlan/include/${PLATFORM_NAME}
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/wlan
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/cmnos
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/wmi
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/adf
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/buf_pool
	${CMAKE_SOURCE_DIR}/magpie_fw_dev/target/htc
)

ADD_LIBRARY(firmware ${SOURCES})

ADD_CUSTOM_COMMAND(
	OUTPUT fw.elf
	DEPENDS firmware
	COMMAND ${CMAKE_C_COMPILER}
		-nostdlib
		-Wl,--start-group
		${CMAKE_BINARY_DIR}/libfirmware.a
		-Wl,--end-group
		-Wl,-T,${CMAKE_SOURCE_DIR}/ram-${PLATFORM_NAME}.ld
		-Wl,-T,${CMAKE_SOURCE_DIR}/rom-addrs-${PLATFORM_NAME}.ld
		-o fw.elf
)
ADD_CUSTOM_COMMAND(
	OUTPUT fw.bin
	DEPENDS fw.elf
	COMMAND ${CMAKE_OBJCOPY}
		--change-section-lma .boot-0x400000
		--change-section-vma .boot-0x400000
		--change-section-lma .text-0x400000
		--change-section-vma .text-0x400000
		-O binary fw.elf fw.bin
)
ADD_CUSTOM_COMMAND(
	OUTPUT ${FIRMWARE_NAME}
	DEPENDS fw.bin
	COMMAND ${CMAKE_SOURCE_DIR}/firmware-crc.pl < fw.bin > ${FIRMWARE_NAME}
)
ADD_CUSTOM_TARGET(gen-firmware ALL DEPENDS ${FIRMWARE_NAME})
