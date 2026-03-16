// Fill out your copyright notice in the Description page of Project Settings.


#include "APizeoSensorInput.h"

#include "Kismet/GameplayStatics.h"
#include "RMVR/Character/RMVRCharacterBase.h"
#if PLATFORM_WINDOWS
#include "Windows/AllowWindowsPlatformTypes.h"
#include <windows.h>
#include "Windows/HideWindowsPlatformTypes.h"
#endif

#include <string>
#include "HAL/PlatformProcess.h"

#include "Async/Async.h"

APizeoSensorInput::APizeoSensorInput()
{
    PrimaryActorTick.bCanEverTick = false;

    SerialHandle = nullptr;
    bRunning = false;
}


void APizeoSensorInput::BeginPlay()
{
    Super::BeginPlay();
    StartSerial();
}


void APizeoSensorInput::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    StopSerial();
    Super::EndPlay(EndPlayReason);
}


void APizeoSensorInput::StartSerial()
{
#if PLATFORM_WINDOWS

    FString FullPort = "\\\\.\\" + PortName;

    HANDLE Handle = CreateFile(
        *FullPort,
        GENERIC_READ,
        0,
        nullptr,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        nullptr);

    if (Handle == INVALID_HANDLE_VALUE)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to open %s"), *PortName);
        return;
    }

    SerialHandle = Handle;

    DCB Params = {0};
    Params.DCBlength = sizeof(Params);

    GetCommState(Handle, &Params);

    Params.BaudRate = BaudRate;
    Params.ByteSize = 8;
    Params.StopBits = ONESTOPBIT;
    Params.Parity = NOPARITY;

    SetCommState(Handle, &Params);

    COMMTIMEOUTS Timeouts = {0};

    Timeouts.ReadIntervalTimeout = 1;
    Timeouts.ReadTotalTimeoutConstant = 1;
    Timeouts.ReadTotalTimeoutMultiplier = 0;

    SetCommTimeouts(Handle, &Timeouts);

    bRunning = true;

    WorkerThread = Async(EAsyncExecution::Thread, [this]()
    {
        SerialWorker();
    });

    UE_LOG(LogTemp, Warning, TEXT("Pizeo serial connected to %s"), *PortName);

#endif
}


void APizeoSensorInput::SerialWorker()
{
#if PLATFORM_WINDOWS

    HANDLE Handle = (HANDLE)SerialHandle;

    char TempBuffer[256];
    DWORD BytesRead;

    while (bRunning)
    {
        if (!ReadFile(Handle, TempBuffer, sizeof(TempBuffer), &BytesRead, NULL))
        {
            continue;
        }

        if (BytesRead == 0)
            continue;

        FString Incoming = FString(ANSI_TO_TCHAR(std::string(TempBuffer, BytesRead).c_str()));

        Buffer += Incoming;

        int32 NewlineIndex;

        while (Buffer.FindChar('\n', NewlineIndex))
        {
            FString Line = Buffer.Left(NewlineIndex).TrimStartAndEnd();

            Buffer = Buffer.Mid(NewlineIndex + 1);

            if (!Line.IsNumeric())
                continue;

            int32 SensorIndex = FCString::Atoi(*Line);

            AsyncTask(ENamedThreads::GameThread, [this, SensorIndex]()
            {
                UE_LOG(LogTemp, Warning, TEXT("Pizeo hit: %d"), SensorIndex);

                OnPiezoHit.Broadcast(SensorIndex);
            });
        }

        FPlatformProcess::Sleep(0.001f);
    }

#endif
}


void APizeoSensorInput::StopSerial()
{
#if PLATFORM_WINDOWS

    bRunning = false;

    if (SerialHandle)
    {
        HANDLE Handle = (HANDLE)SerialHandle;

        CancelIoEx(Handle, NULL);

        CloseHandle(Handle);

        SerialHandle = nullptr;
    }

#endif
}