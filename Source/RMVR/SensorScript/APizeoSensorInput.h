
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RMVR/Character/RMVRCharacterBase.h"

#include "APizeoSensorInput.generated.h"
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnPizeoHit, int32, SensorIndex);

UCLASS()
class RMVR_API APizeoSensorInput : public AActor
{
	GENERATED_BODY()

public:

	APizeoSensorInput();

protected:

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

public:

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Serial")
	FString PortName = "COM7";

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Serial")
	int32 BaudRate = 115200;

	UPROPERTY(BlueprintAssignable, Category="Pizeo")
	FOnPizeoHit OnPiezoHit;

private:

	void StartSerial();
	void StopSerial();
	void SerialWorker();

private:

	void* SerialHandle;

	FString Buffer;

	bool bRunning;

	TFuture<void> WorkerThread;
};