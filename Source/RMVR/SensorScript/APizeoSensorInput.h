
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Character/RMVRCharacterBase.h"

#include "PizeoSensorInput.generated.h"

UCLASS()
class RMVR_API APizeoSensorInput : public AActor
{
	GENERATED_BODY()
	
public:	
	// Sets default values for this actor's properties
	APizeoSensorInput();

	// Select BP_ThirdPersonCharacter in editor
	UPROPERTY(EditAnywhere, Category = "Target")
	TSubclassOf<ARMVRCharacterBase> TargetCharacterClass;

	UPROPERTY(EditAnywhere, Category = "Hand Highlight")
	int32 PointIndex = 0;


protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

public:	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

};
