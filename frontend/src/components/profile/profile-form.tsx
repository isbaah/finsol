"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { ApiError } from "@/lib/api-client";
import { applyDrfErrors } from "@/lib/drf-errors";
import { useMyProfile, useSaveProfile } from "@/features/profile/use-profile";
import type { CustomerProfile, ProfilePayload } from "@/features/profile/types";
import { type ProfileFormValues, profileSchema } from "@/schemas/profile";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

const EMPTY_VALUES: ProfileFormValues = {
  first_name: "",
  last_name: "",
  phone_number_e164: "",
  address_line_1: "",
  address_line_2: "",
  city: "",
  preferred_disbursement_method: "MOBILE_MONEY",
  mobile_money_network: undefined,
  mobile_money_number: "",
  bank_name: "",
  bank_account_name: "",
  bank_account_number: "",
  declaration: false,
};

function toFormValues(profile: CustomerProfile): ProfileFormValues {
  return {
    first_name: profile.first_name,
    last_name: profile.last_name,
    phone_number_e164: profile.phone_number_e164,
    address_line_1: profile.address_line_1,
    address_line_2: profile.address_line_2,
    city: profile.city,
    preferred_disbursement_method: profile.preferred_disbursement_method,
    mobile_money_network: profile.mobile_money_network || undefined,
    mobile_money_number: profile.mobile_money_number,
    bank_name: profile.bank_name,
    bank_account_name: profile.bank_account_name,
    bank_account_number: profile.bank_account_number,
    declaration: true,
  };
}

export function ProfileForm() {
  const router = useRouter();
  const { data: profile, isLoading } = useMyProfile();
  const saveProfile = useSaveProfile();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const isFirstCompletion = !isLoading && !profile;

  const {
    register,
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: EMPTY_VALUES,
  });

  useEffect(() => {
    if (profile) reset(toFormValues(profile));
  }, [profile, reset]);

  // useWatch (not the form-level watch() function) so the React Compiler
  // can still memoize this component — watch() returns a plain function
  // React Compiler can't safely wrap, but useWatch is a normal subscribed
  // hook value.
  const method = useWatch({ control, name: "preferred_disbursement_method" });

  const onSubmit = async (values: ProfileFormValues) => {
    setSubmitError(null);
    const payload: ProfilePayload = {
      first_name: values.first_name,
      last_name: values.last_name,
      phone_number_e164: values.phone_number_e164,
      address_line_1: values.address_line_1,
      address_line_2: values.address_line_2,
      city: values.city,
      preferred_disbursement_method: values.preferred_disbursement_method,
      mobile_money_network: values.mobile_money_network,
      mobile_money_number: values.mobile_money_number,
      bank_name: values.bank_name,
      bank_account_name: values.bank_account_name,
      bank_account_number: values.bank_account_number,
    };
    try {
      await saveProfile.mutateAsync(payload);
      toast.success(isFirstCompletion ? "Profile completed." : "Profile updated.");
      if (isFirstCompletion) router.push("/dashboard");
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        applyDrfErrors(error, setError, "phone_number_e164");
        return;
      }
      setSubmitError("Something went wrong saving your profile. Please try again.");
    }
  };

  if (isLoading) {
    return <p className="text-muted-foreground text-sm">Loading…</p>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex w-full max-w-md flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="first_name">First name</Label>
          <Input id="first_name" autoComplete="given-name" {...register("first_name")} />
          {errors.first_name && (
            <p className="text-destructive text-sm">{errors.first_name.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="last_name">Last name</Label>
          <Input id="last_name" autoComplete="family-name" {...register("last_name")} />
          {errors.last_name && (
            <p className="text-destructive text-sm">{errors.last_name.message}</p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="phone_number_e164">Phone number</Label>
        <Input
          id="phone_number_e164"
          type="tel"
          placeholder="024 123 4567"
          autoComplete="tel"
          {...register("phone_number_e164")}
        />
        {errors.phone_number_e164 && (
          <p className="text-destructive text-sm">{errors.phone_number_e164.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="address_line_1">Address line 1</Label>
        <Input id="address_line_1" autoComplete="address-line1" {...register("address_line_1")} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="address_line_2">Address line 2</Label>
        <Input id="address_line_2" autoComplete="address-line2" {...register("address_line_2")} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="city">City</Label>
        <Input id="city" autoComplete="address-level2" {...register("city")} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="preferred_disbursement_method">Payout method</Label>
        <Select id="preferred_disbursement_method" {...register("preferred_disbursement_method")}>
          <option value="MOBILE_MONEY">Mobile Money</option>
          <option value="BANK">Bank</option>
        </Select>
        {errors.preferred_disbursement_method && (
          <p className="text-destructive text-sm">{errors.preferred_disbursement_method.message}</p>
        )}
      </div>

      {method === "MOBILE_MONEY" && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mobile_money_network">Mobile money network</Label>
            <Select id="mobile_money_network" {...register("mobile_money_network")}>
              <option value="">Select a network</option>
              <option value="MTN">MTN Mobile Money</option>
              <option value="TELECEL">Telecel Cash</option>
              <option value="AIRTELTIGO">AirtelTigo Money</option>
              <option value="OTHER">Other</option>
            </Select>
            {errors.mobile_money_network && (
              <p className="text-destructive text-sm">{errors.mobile_money_network.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mobile_money_number">Mobile money number</Label>
            <Input id="mobile_money_number" type="tel" {...register("mobile_money_number")} />
            {errors.mobile_money_number && (
              <p className="text-destructive text-sm">{errors.mobile_money_number.message}</p>
            )}
          </div>
        </>
      )}

      {method === "BANK" && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="bank_name">Bank name</Label>
            <Input id="bank_name" {...register("bank_name")} />
            {errors.bank_name && (
              <p className="text-destructive text-sm">{errors.bank_name.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="bank_account_name">Account name</Label>
            <Input id="bank_account_name" {...register("bank_account_name")} />
            {errors.bank_account_name && (
              <p className="text-destructive text-sm">{errors.bank_account_name.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="bank_account_number">Account number</Label>
            <Input id="bank_account_number" {...register("bank_account_number")} />
            {errors.bank_account_number && (
              <p className="text-destructive text-sm">{errors.bank_account_number.message}</p>
            )}
          </div>
        </>
      )}

      <Controller<ProfileFormValues, "declaration">
        control={control}
        name="declaration"
        render={({ field }) => (
          <div className="flex items-start gap-2">
            <Checkbox
              id="declaration"
              checked={field.value ?? false}
              onCheckedChange={(checked) => field.onChange(checked)}
            />
            <Label htmlFor="declaration" className="text-muted-foreground text-sm font-normal">
              The information I provide is accurate.
            </Label>
          </div>
        )}
      />
      {errors.declaration && (
        <p className="text-destructive text-sm">{errors.declaration.message}</p>
      )}

      {submitError && <p className="text-destructive text-sm">{submitError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Saving…" : isFirstCompletion ? "Complete profile" : "Save changes"}
      </Button>
    </form>
  );
}
