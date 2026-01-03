


#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "PiezoSensorReceiver.generated.h"



UCLASS()
class RMVR_API APiezoSensorReceiver : public AActor
{
	GENERATED_BODY()
	
public:	
	// Sets default values for this actor's properties
	APiezoSensorReceiver();

protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

public:	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

	
	
};
