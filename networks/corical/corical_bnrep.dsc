belief network "unknown"
node Age {
  type : discrete [ 8 ] = { "0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+" };
}
node AZVaccineDoses {
  type : discrete [ 3 ] = { "None", "One", "Two" };
}
node BackgroundCSVTOver6Weeks {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node BackgroundPVTOver6Weeks {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node Covid19AssociatedCSVT {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node Covid19AssociatedPVT {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node DieFromBackgroundCSVT {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node DieFromBackgroundPVT {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node DieFromCovid19 {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node DieFromCovid19AssociatedCSVT {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node DieFromCovid19AssociatedPVT {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node DieFromVaccineAssociatedTTS {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node IntensityOfCommunityTransmission {
  type : discrete [ 10 ] = { "None", "ATAGI Low", "ATAGI Med", "ATAGI High", "One Percent", "Two Percent", "NSW 200 Daily", "NSW 1000 Daily", "VIC 1000 Daily", "QLD 1000 Daily" };
}
node RiskOfSymptomaticInfection {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node RiskOfSymptomaticInfectionUnderCurrentTransmissionAndVaccinationStatus {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node SARSCoV2Variant {
  type : discrete [ 2 ] = { "Alpha Wild", "Delta" };
}
node Sex {
  type : discrete [ 2 ] = { "Male", "Female" };
}
node VaccineAssociatedTTS {
  type : discrete [ 2 ] = { "Yes", "No" };
}
node VaccineEffectivenessAgainstDeathIfInfected {
  type : discrete [ 2 ] = { "Effective", "Not Effective" };
}
node VaccineEffectivenessAgainstSymptomaticInfection {
  type : discrete [ 2 ] = { "Effective", "Not Effective" };
}
probability ( Age ) {
   0.1233831, 0.1233831, 0.1402985, 0.1452736, 0.1273632, 0.1213930, 0.1044776, 0.1144279;
}
probability ( AZVaccineDoses ) {
   0.30, 0.35, 0.35;
}
probability ( BackgroundCSVTOver6Weeks | Age ) {
  (0) : 0.00000038, 0.99999962;
  (1) : 0.00000038, 0.99999962;
  (2) : 0.00000064, 0.99999936;
  (3) : 0.00000064, 0.99999936;
  (4) : 0.00000064, 0.99999936;
  (5) : 0.00000075, 0.99999925;
  (6) : 0.00000075, 0.99999925;
  (7) : 0.00000073, 0.99999927;
}
probability ( BackgroundPVTOver6Weeks | Age ) {
  (0) : 0.0, 1.0;
  (1) : 0.0, 1.0;
  (2) : 0.0000002, 0.9999998;
  (3) : 0.00000026, 0.99999974;
  (4) : 0.00000056, 0.99999944;
  (5) : 0.00000091, 0.99999909;
  (6) : 0.00000176, 0.99999824;
  (7) : 0.00000196, 0.99999804;
}
probability ( Covid19AssociatedCSVT | RiskOfSymptomaticInfectionUnderCurrentTransmissionAndVaccinationStatus, Sex ) {
  (0, 0) : 0.0000288732, 0.9999711268;
  (1, 0) : 0.0, 1.0;
  (0, 1) : 0.0000541969, 0.9999458031;
  (1, 1) : 0.0, 1.0;
}
probability ( Covid19AssociatedPVT | RiskOfSymptomaticInfectionUnderCurrentTransmissionAndVaccinationStatus, Sex ) {
  (0, 0) : 0.000482596, 0.999517404;
  (1, 0) : 0.0, 1.0;
  (0, 1) : 0.000318407, 0.999681593;
  (1, 1) : 0.0, 1.0;
}
probability ( DieFromBackgroundCSVT | BackgroundCSVTOver6Weeks ) {
  (0) : 0.07, 0.93;
  (1) : 0.0, 1.0;
}
probability ( DieFromBackgroundPVT | BackgroundPVTOver6Weeks ) {
  (0) : 0.27, 0.73;
  (1) : 0.0, 1.0;
}
probability ( DieFromCovid19 | Age, RiskOfSymptomaticInfectionUnderCurrentTransmissionAndVaccinationStatus, Sex, VaccineEffectivenessAgainstDeathIfInfected ) {
  (0, 0, 0, 0) : 0.0, 1.0;
  (1, 0, 0, 0) : 0.0, 1.0;
  (2, 0, 0, 0) : 0.0, 1.0;
  (3, 0, 0, 0) : 0.0, 1.0;
  (4, 0, 0, 0) : 0.0, 1.0;
  (5, 0, 0, 0) : 0.0, 1.0;
  (6, 0, 0, 0) : 0.0, 1.0;
  (7, 0, 0, 0) : 0.0, 1.0;
  (0, 1, 0, 0) : 0.0, 1.0;
  (1, 1, 0, 0) : 0.0, 1.0;
  (2, 1, 0, 0) : 0.0, 1.0;
  (3, 1, 0, 0) : 0.0, 1.0;
  (4, 1, 0, 0) : 0.0, 1.0;
  (5, 1, 0, 0) : 0.0, 1.0;
  (6, 1, 0, 0) : 0.0, 1.0;
  (7, 1, 0, 0) : 0.0, 1.0;
  (0, 0, 1, 0) : 0.0, 1.0;
  (1, 0, 1, 0) : 0.0, 1.0;
  (2, 0, 1, 0) : 0.0, 1.0;
  (3, 0, 1, 0) : 0.0, 1.0;
  (4, 0, 1, 0) : 0.0, 1.0;
  (5, 0, 1, 0) : 0.0, 1.0;
  (6, 0, 1, 0) : 0.0, 1.0;
  (7, 0, 1, 0) : 0.0, 1.0;
  (0, 1, 1, 0) : 0.0, 1.0;
  (1, 1, 1, 0) : 0.0, 1.0;
  (2, 1, 1, 0) : 0.0, 1.0;
  (3, 1, 1, 0) : 0.0, 1.0;
  (4, 1, 1, 0) : 0.0, 1.0;
  (5, 1, 1, 0) : 0.0, 1.0;
  (6, 1, 1, 0) : 0.0, 1.0;
  (7, 1, 1, 0) : 0.0, 1.0;
  (0, 0, 0, 1) : 0.0, 1.0;
  (1, 0, 0, 1) : 0.00030321, 0.99969679;
  (2, 0, 0, 1) : 0.00032457, 0.99967543;
  (3, 0, 0, 1) : 0.00080402, 0.99919598;
  (4, 0, 0, 1) : 0.00086505, 0.99913495;
  (5, 0, 0, 1) : 0.00374787, 0.99625213;
  (6, 0, 0, 1) : 0.01879699, 0.98120301;
  (7, 0, 0, 1) : 0.2174339, 0.7825661;
  (0, 1, 0, 1) : 0.0, 1.0;
  (1, 1, 0, 1) : 0.0, 1.0;
  (2, 1, 0, 1) : 0.0, 1.0;
  (3, 1, 0, 1) : 0.0, 1.0;
  (4, 1, 0, 1) : 0.0, 1.0;
  (5, 1, 0, 1) : 0.0, 1.0;
  (6, 1, 0, 1) : 0.0, 1.0;
  (7, 1, 0, 1) : 0.0, 1.0;
  (0, 0, 1, 1) : 0.0, 1.0;
  (1, 0, 1, 1) : 0.0, 1.0;
  (2, 0, 1, 1) : 0.0, 1.0;
  (3, 0, 1, 1) : 0.00044336, 0.99955664;
  (4, 0, 1, 1) : 0.00062933, 0.99937067;
  (5, 0, 1, 1) : 0.00285919, 0.99714081;
  (6, 0, 1, 1) : 0.00806916, 0.99193084;
  (7, 0, 1, 1) : 0.1910828, 0.8089172;
  (0, 1, 1, 1) : 0.0, 1.0;
  (1, 1, 1, 1) : 0.0, 1.0;
  (2, 1, 1, 1) : 0.0, 1.0;
  (3, 1, 1, 1) : 0.0, 1.0;
  (4, 1, 1, 1) : 0.0, 1.0;
  (5, 1, 1, 1) : 0.0, 1.0;
  (6, 1, 1, 1) : 0.0, 1.0;
  (7, 1, 1, 1) : 0.0, 1.0;
}
probability ( DieFromCovid19AssociatedCSVT | Covid19AssociatedCSVT ) {
  (0) : 0.174, 0.826;
  (1) : 0.0, 1.0;
}
probability ( DieFromCovid19AssociatedPVT | Covid19AssociatedPVT ) {
  (0) : 0.1981982, 0.8018018;
  (1) : 0.0, 1.0;
}
probability ( DieFromVaccineAssociatedTTS | VaccineAssociatedTTS ) {
  (0) : 0.05, 0.95;
  (1) : 0.0, 1.0;
}
probability ( IntensityOfCommunityTransmission ) {
   0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1;
}
probability ( RiskOfSymptomaticInfection | Age, SARSCoV2Variant ) {
  (0, 0) : 0.0416611, 0.9583389;
  (1, 0) : 0.0702759, 0.9297241;
  (2, 0) : 0.1589055, 0.8410945;
  (3, 0) : 0.1212599, 0.8787401;
  (4, 0) : 0.1005435, 0.8994565;
  (5, 0) : 0.0977633, 0.9022367;
  (6, 0) : 0.0812794, 0.9187206;
  (7, 0) : 0.1126984, 0.8873016;
  (0, 1) : 0.09182884, 0.90817116;
  (1, 1) : 0.1423347, 0.8576653;
  (2, 1) : 0.1540069, 0.8459931;
  (3, 1) : 0.1131176, 0.8868824;
  (4, 1) : 0.09119044, 0.90880956;
  (5, 1) : 0.09033166, 0.90966834;
  (6, 1) : 0.05484361, 0.94515639;
  (7, 1) : 0.04305606, 0.95694394;
}
probability ( RiskOfSymptomaticInfectionUnderCurrentTransmissionAndVaccinationStatus | IntensityOfCommunityTransmission, RiskOfSymptomaticInfection, VaccineEffectivenessAgainstSymptomaticInfection ) {
  (0, 0, 0) : 0.0, 1.0;
  (1, 0, 0) : 0.0, 1.0;
  (2, 0, 0) : 0.0, 1.0;
  (3, 0, 0) : 0.0, 1.0;
  (4, 0, 0) : 0.0, 1.0;
  (5, 0, 0) : 0.0, 1.0;
  (6, 0, 0) : 0.0, 1.0;
  (7, 0, 0) : 0.0, 1.0;
  (8, 0, 0) : 0.0, 1.0;
  (9, 0, 0) : 0.0, 1.0;
  (0, 1, 0) : 0.0, 1.0;
  (1, 1, 0) : 0.0, 1.0;
  (2, 1, 0) : 0.0, 1.0;
  (3, 1, 0) : 0.0, 1.0;
  (4, 1, 0) : 0.0, 1.0;
  (5, 1, 0) : 0.0, 1.0;
  (6, 1, 0) : 0.0, 1.0;
  (7, 1, 0) : 0.0, 1.0;
  (8, 1, 0) : 0.0, 1.0;
  (9, 1, 0) : 0.0, 1.0;
  (0, 0, 1) : 0.0, 1.0;
  (1, 0, 1) : 0.00471, 0.99529;
  (2, 0, 1) : 0.04469, 0.95531;
  (3, 0, 1) : 0.5759, 0.4241;
  (4, 0, 1) : 0.1, 0.9;
  (5, 0, 1) : 0.2, 0.8;
  (6, 0, 1) : 0.04455, 0.95545;
  (7, 0, 1) : 0.22276, 0.77724;
  (8, 0, 1) : 0.27289, 0.72711;
  (9, 0, 1) : 0.35067, 0.64933;
  (0, 1, 1) : 0.0, 1.0;
  (1, 1, 1) : 0.0, 1.0;
  (2, 1, 1) : 0.0, 1.0;
  (3, 1, 1) : 0.0, 1.0;
  (4, 1, 1) : 0.0, 1.0;
  (5, 1, 1) : 0.0, 1.0;
  (6, 1, 1) : 0.0, 1.0;
  (7, 1, 1) : 0.0, 1.0;
  (8, 1, 1) : 0.0, 1.0;
  (9, 1, 1) : 0.0, 1.0;
}
probability ( SARSCoV2Variant ) {
   0.05, 0.95;
}
probability ( Sex ) {
   0.5, 0.5;
}
probability ( VaccineAssociatedTTS | Age, AZVaccineDoses ) {
  (0, 0) : 0.0, 1.0;
  (1, 0) : 0.0, 1.0;
  (2, 0) : 0.0, 1.0;
  (3, 0) : 0.0, 1.0;
  (4, 0) : 0.0, 1.0;
  (5, 0) : 0.0, 1.0;
  (6, 0) : 0.0, 1.0;
  (7, 0) : 0.0, 1.0;
  (0, 1) : 0.000025, 0.999975;
  (1, 1) : 0.000025, 0.999975;
  (2, 1) : 0.000025, 0.999975;
  (3, 1) : 0.000025, 0.999975;
  (4, 1) : 0.000025, 0.999975;
  (5, 1) : 0.000027, 0.999973;
  (6, 1) : 0.000016, 0.999984;
  (7, 1) : 0.0000185, 0.9999815;
  (0, 2) : 0.0000018, 0.9999982;
  (1, 2) : 0.0000018, 0.9999982;
  (2, 2) : 0.0000018, 0.9999982;
  (3, 2) : 0.0000018, 0.9999982;
  (4, 2) : 0.0000018, 0.9999982;
  (5, 2) : 0.0000018, 0.9999982;
  (6, 2) : 0.0000018, 0.9999982;
  (7, 2) : 0.0000018, 0.9999982;
}
probability ( VaccineEffectivenessAgainstDeathIfInfected | AZVaccineDoses, SARSCoV2Variant ) {
  (0, 0) : 0.0, 1.0;
  (1, 0) : 0.8, 0.2;
  (2, 0) : 0.95, 0.05;
  (0, 1) : 0.0, 1.0;
  (1, 1) : 0.69, 0.31;
  (2, 1) : 0.9, 0.1;
}
probability ( VaccineEffectivenessAgainstSymptomaticInfection | AZVaccineDoses, SARSCoV2Variant ) {
  (0, 0) : 0.0, 1.0;
  (1, 0) : 0.6, 0.4;
  (2, 0) : 0.8, 0.2;
  (0, 1) : 0.0, 1.0;
  (1, 1) : 0.3333333, 0.6666667;
  (2, 1) : 0.61, 0.39;
}
