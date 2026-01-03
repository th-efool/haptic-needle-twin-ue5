// Fill out your copyright notice in the Description page of Project Settings.


#include "PizeoSensorInput.h"
#include "RMVR/Character/RMVRCharacterBase.h"


// Sets default values
APizeoSensorInput::APizeoSensorInput()
{
 	// Set this actor to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;

}

// Called when the game starts or when spawned
void APizeoSensorInput::BeginPlay()
{
    Super::BeginPlay();

    if (!TargetCharacterClass)
        return;

    AActor* foundActor =
        UGameplayStatics::GetActorOfClass(GetWorld(), TargetCharacterClass);

    ARMVRCharacterBase* character =
        Cast<ARMVRCharacterBase>(foundActor);

    if (!character)
        return;

    character->RHighlightHandPoint(PointIndex);
}

// Called every frame
void APizeoSensorInput::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

