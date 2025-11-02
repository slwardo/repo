#!/bin/bash

# --- Script to help diagnose Prometheus "connection refused" errors in GKE ---

# --- Configuration ---
# Set to true to show full kubectl errors if commands fail
SHOW_ERRORS=false

# --- Helper Functions ---
print_step() {
    echo ""
    echo "-----------------------------------"
    echo "STEP $1: $2"
    echo "-----------------------------------"
}

print_error() {
    echo "ERROR: $1"
    if $SHOW_ERRORS && [ -n "$2" ]; then
        echo "--- Error Details ---"
        echo "$2"
        echo "---------------------"
    fi
}

print_warning() {
    echo "WARNING: $1"
}

print_info() {
    echo "-> $1"
}

print_result() {
    echo "   $1"
}

# --- Argument Handling ---
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <POD_NAME> <NAMESPACE> <TARGET_IP> <PORT>"
    echo "  <POD_NAME>   : Name of the pod being scraped"
    echo "  <NAMESPACE>  : Namespace of the pod"
    echo "  <TARGET_IP>  : IP address the scrape is currently targeting"
    echo "  <PORT>       : Port the scrape is targeting"
    exit 1
fi

POD_NAME="$1"
NAMESPACE="$2"
TARGET_IP="$3" # IP currently being scraped
PORT="$4"

echo "--- Troubleshooting Scrape Target ---"
echo "Pod Name:      $POD_NAME"
echo "Namespace:     $NAMESPACE"
echo "Target IP:     $TARGET_IP"
echo "Target Port:   $PORT"

# --- Variables ---
POD_IP=""
NODE_NAME=""
POD_STATUS=""
USES_HOST_NETWORK=false
CORRECT_IP=""
IP_MISMATCH=false
LISTENING_ON_LOCALHOST=false
CHECKED_LISTENING=false # Tracks if listening check (log/exec) gave a result
LISTENING_EXTERNALLY=false # Tracks if confirmed listening externally

# --- Step 1: Check Pod Status & Location ---
print_step 1 "Checking Pod Status and Location"
POD_INFO_WIDE=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o wide 2>&1)
if [ $? -ne 0 ]; then
    print_error "Failed to get pod info. Check name/namespace or kubectl setup." "$POD_INFO_WIDE"
    exit 1
fi
print_info "Raw 'kubectl get pod ... -o wide' output:"
print_result "$POD_INFO_WIDE"

# Extract info using awk - handles potential extra spaces
POD_IP=$(echo "$POD_INFO_WIDE" | awk 'NR==2 {print $6}')
NODE_NAME=$(echo "$POD_INFO_WIDE" | awk 'NR==2 {print $7}')
POD_STATUS=$(echo "$POD_INFO_WIDE" | awk 'NR==2 {print $3}')

print_info "Extracted Info:"
print_result "Pod Status: $POD_STATUS"
print_result "Pod IP: $POD_IP"
print_result "Node Name: $NODE_NAME"

if [ "$POD_STATUS" != "Running" ]; then
    print_warning "Pod status is '$POD_STATUS', not 'Running'. This might be the primary issue."
fi

# --- Step 2: Check hostNetwork ---
print_step 2 "Checking hostNetwork Status"
HOST_NETWORK_OUTPUT=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o yaml 2>&1 | grep 'hostNetwork:' | head -n 1) # head -n 1 in case it appears multiple times
if [ $? -ne 0 ]; then
    # Grep exits non-zero if not found OR if kubectl failed
    KUBECTL_EXIT_CODE=$?
    if echo "$HOST_NETWORK_OUTPUT" | grep -q "NotFound"; then
         print_error "Failed to get pod YAML - pod not found?" "$HOST_NETWORK_OUTPUT"
         exit 1
    elif [ $KUBECTL_EXIT_CODE -ne 1 ]; then # Exit code 1 means grep found nothing, >1 means kubectl error
         print_error "Failed to get pod YAML." "$HOST_NETWORK_OUTPUT"
         exit 1
    fi
    # If grep simply found nothing, it's not an error for this check
fi

if echo "$HOST_NETWORK_OUTPUT" | grep -q 'hostNetwork: true'; then
    USES_HOST_NETWORK=true
    print_info "hostNetwork: true"
else
    print_info "hostNetwork: false (or not set)"
fi

# --- Step 3: Determine Correct Target IP ---
print_step 3 "Determining Correct Target IP"
if $USES_HOST_NETWORK; then
    print_info "hostNetwork is true, need Node IP for '$NODE_NAME'."
    NODE_INFO_WIDE=$(kubectl get node "$NODE_NAME" -o wide 2>&1)
     if [ $? -ne 0 ]; then
        print_error "Failed to get node info for '$NODE_NAME'." "$NODE_INFO_WIDE"
        print_warning "Cannot determine correct target IP automatically."
     else
         print_info "Raw 'kubectl get node ... -o wide' output:"
         print_result "$NODE_INFO_WIDE"
         CORRECT_IP=$(echo "$NODE_INFO_WIDE" | awk 'NR==2 {print $6}')
         print_info "Correct IP should be Node Internal IP: $CORRECT_IP"
     fi
else
    CORRECT_IP="$POD_IP"
    print_info "hostNetwork is false, correct IP should be Pod IP: $CORRECT_IP"
fi

# --- Step 4: Compare Target IPs ---
print_step 4 "Comparing Target IP vs Correct IP"
if [ -n "$CORRECT_IP" ]; then
    if [ "$TARGET_IP" != "$CORRECT_IP" ]; then
        IP_MISMATCH=true
        print_warning "MISMATCH! Target IP ($TARGET_IP) DOES NOT MATCH Correct IP ($CORRECT_IP)."
        print_info "Suggestion: Fix Prometheus scrape configuration to target $CORRECT_IP."
    else
        print_info "OK: Target IP ($TARGET_IP) matches Correct IP ($CORRECT_IP)."
    fi
else
    print_info "Skipped comparison as Correct IP could not be determined."
fi

# --- Step 5: Check How Pod is Listening ---
print_step 5 "Checking How Pod is Listening (Logs & Exec)"
# Find container names
print_info "Finding container names..."
CONTAINER_NAMES=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.containers[*].name}' 2>/dev/null)
if [ -z "$CONTAINER_NAMES" ]; then
    print_error "Could not get container names for pod '$POD_NAME'." ""
    print_warning "Skipping listening checks."
else
     print_info "Found container(s): $CONTAINER_NAMES"

     # Check logs for each container
     print_info "Checking recent logs (last 100 lines) for listening address clues..."
     for CONTAINER_NAME in $CONTAINER_NAMES; do
         print_info "Analyzing logs for container '$CONTAINER_NAME'..."
         LOGS=$(kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --tail=100 2>&1)
         if [ $? -ne 0 ]; then
              print_warning "Could not get logs for container '$CONTAINER_NAME'."
         else
              # Check for explicit localhost binding for the target port
              if echo "$LOGS" | grep -Eq "(localhost|127\.0\.0\.1):$PORT"; then
                   print_warning "FOUND IN LOGS: Container '$CONTAINER_NAME' seems configured to listen on localhost:$PORT!"
                   LISTENING_ON_LOCALHOST=true
                   CHECKED_LISTENING=true
                   break # Found definitive answer for this pod
              # Check for general localhost binding messages (less specific)
              elif echo "$LOGS" | grep -Eq 'Listening on localhost:|Listening on 127\.0\.0\.1:|--metrics-addr=localhost:|--listen-address=127\.0\.0\.1'; then
                   print_warning "FOUND INDICATION IN LOGS: Container '$CONTAINER_NAME' might be listening on localhost (port not confirmed in same line)."
                   # Don't set CHECKED_LISTENING=true yet, try exec for confirmation
              fi
              # Check for explicit external binding for the target port
               if echo "$LOGS" | grep -Eq "(0\.0\.0\.0|\*|\[::\]):$PORT"; then
                    print_info "FOUND IN LOGS: Container '$CONTAINER_NAME' seems configured to listen externally on port $PORT."
                    LISTENING_EXTERNALLY=true # Set flag indicating external listen found
                    CHECKED_LISTENING=true # Consider this checked
                    break # Found definitive answer for this pod
               fi
         fi
     done

     # If logs weren't conclusive about localhost:PORT, try exec
     if ! $CHECKED_LISTENING && ! $LISTENING_ON_LOCALHOST; then
         print_info "Logs inconclusive for localhost:$PORT binding. Attempting 'exec' (may fail if tools not present)..."
          for CONTAINER_NAME in $CONTAINER_NAMES; do
              if $CHECKED_LISTENING; then break; fi # Stop if previous container check was conclusive

              print_info "Trying 'ss -tulnp' in container '$CONTAINER_NAME'..."
              EXEC_OUT=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" -- ss -tulnp 2>&1)
              if [ $? -eq 0 ]; then
                   print_info "'ss' output:"
                   print_result "$EXEC_OUT"
                   if echo "$EXEC_OUT" | grep -Eq "LISTEN\s+.*\s+(127\.0\.0\.1|localhost|\[::1\]):$PORT\b"; then
                        print_warning "FOUND VIA EXEC (ss): Container '$CONTAINER_NAME' listens on localhost:$PORT!"
                        LISTENING_ON_LOCALHOST=true
                        CHECKED_LISTENING=true
                   elif echo "$EXEC_OUT" | grep -Eq "LISTEN\s+.*\s+(0\.0\.0\.0|\*|\[::\]):$PORT\b"; then
                        print_info "FOUND VIA EXEC (ss): Container '$CONTAINER_NAME' listens externally (0.0.0.0 or *) on port $PORT."
                        LISTENING_EXTERNALLY=true
                        CHECKED_LISTENING=true
                   else
                        print_info "'ss' output doesn't show expected listener on port $PORT for localhost or external."
                   fi
                   # Even if port not found, ss worked, so consider check attempted for this container
              else
                   print_info "'ss' command failed or not found in container '$CONTAINER_NAME'. Trying 'netstat'..."
                   EXEC_OUT=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" -- netstat -tulnp 2>&1)
                   if [ $? -eq 0 ]; then
                        print_info "'netstat' output:"
                        print_result "$EXEC_OUT"
                       if echo "$EXEC_OUT" | grep -Eq "(tcp|tcp6)\s+.*\s+(127\.0\.0\.1|localhost|::1):$PORT\s+.*LISTEN"; then
                            print_warning "FOUND VIA EXEC (netstat): Container '$CONTAINER_NAME' listens on localhost:$PORT!"
                            LISTENING_ON_LOCALHOST=true
                            CHECKED_LISTENING=true
                       elif echo "$EXEC_OUT" | grep -Eq "(tcp|tcp6)\s+.*\s+(0\.0\.0\.0|\*|::):$PORT\s+.*LISTEN"; then
                           print_info "FOUND VIA EXEC (netstat): Container '$CONTAINER_NAME' listens externally (0.0.0.0 or *) on port $PORT."
                           LISTENING_EXTERNALLY=true
                           CHECKED_LISTENING=true
                       else
                           print_info "'netstat' output doesn't show expected listener on port $PORT for localhost or external."
                       fi
                       # Netstat worked, consider check attempted
                   else
                       print_warning "'netstat' command failed or not found in container '$CONTAINER_NAME'."
                   fi
              fi

              # If we confirmed either way via exec, break the loop
              if $CHECKED_LISTENING; then break; fi
         done # end loop through containers for exec
     fi # end if exec needed

     if ! $CHECKED_LISTENING && ! $LISTENING_ON_LOCALHOST && ! $LISTENING_EXTERNALLY; then
          print_warning "Could not definitively determine listening address via logs or exec."
     fi
fi # end if container names found

# --- Step 6: Check Network Policies ---
print_step 6 "Checking Network Policies in namespace '$NAMESPACE'"
NETPOL=$(kubectl get networkpolicy -n "$NAMESPACE" 2>&1)
NETPOL_EXIT_CODE=$?
# Check if exit code is non-zero AND output doesn't contain "No resources found"
if [ $NETPOL_EXIT_CODE -ne 0 ] && ! echo "$NETPOL" | grep -q "No resources found"; then
     print_error "Failed to check NetworkPolicies." "$NETPOL"
elif echo "$NETPOL" | grep -q "No resources found"; then
     print_info "No NetworkPolicies found in namespace '$NAMESPACE'."
else
     print_warning "Found NetworkPolicies. Manual analysis needed if they might be blocking traffic."
     print_info "Raw 'kubectl get networkpolicy...' output:"
     print_result "$NETPOL"
fi

# --- Step 7: Summary ---
print_step 7 "Summary of Findings"

FINAL_CAUSE="Unknown"

if $IP_MISMATCH; then
    echo "* LIKELY CAUSE: Target IP ($TARGET_IP) does not match the correct Pod/Node IP ($CORRECT_IP)."
    echo "* RECOMMENDATION: Update Prometheus scrape configuration to target '$CORRECT_IP'."
    FINAL_CAUSE="IP Mismatch"
elif $LISTENING_ON_LOCALHOST; then
     echo "* LIKELY CAUSE: The application inside the pod is listening only on localhost:$PORT (127.0.0.1)."
     echo "* RECOMMENDATION: Application cannot be scraped externally on IP '$TARGET_IP' for this port as configured."
     echo "  -> Either reconfigure the application to listen on '0.0.0.0:$PORT' (if possible/supported)"
     echo "  -> Or confirm this specific port/endpoint is not meant for external scraping via PodMonitoring."
     FINAL_CAUSE="Listens on Localhost Only"
elif $LISTENING_EXTERNALLY; then
     echo "* INFO: Target IP appears correct, and application seems to be listening externally on port $PORT."
     echo "* RECOMMENDATION: 'Connection Refused' is unexpected if listener confirmed. Check:"
     echo "  -> NetworkPolicies (Step 8) if any exist."
     echo "  -> GCP Firewall rules (outside Kubernetes)."
     echo "  -> Intermittent application errors or crashes (check full logs)."
     FINAL_CAUSE="External Listener OK - Check Network/App"
else # Catch-all if checks failed or were inconclusive
     echo "* INFO: Analysis inconclusive. Could not confirm IP mismatch or localhost binding via automated checks."
      echo "* RECOMMENDATION: Review script output above for errors or warnings."
      echo "  -> Manually verify pod/node IPs and check application configuration/documentation for the correct metrics port and listening address."
      echo "  -> Check NetworkPolicies (Step 8) and GCP Firewalls."
      FINAL_CAUSE="Inconclusive - Manual Check Needed"
 fi

echo ""
echo "Final Diagnosis Suggestion: $FINAL_CAUSE"
echo "-----------------------------------"

exit 0

